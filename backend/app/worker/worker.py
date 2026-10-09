"""
Background worker process for PostgreSQL task queue.

Executes claimed tasks in bounded concurrency with lease renewal,
crash recovery, and graceful shutdown.
"""

from __future__ import annotations

import logging
import signal
import time
import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.task import Task
from app.services.task_queue_service import TaskQueueService
from app.worker.handlers import TASK_HANDLERS

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """
    Independent worker process that polls and executes tasks from the PostgreSQL queue.
    """

    def __init__(
        self,
        worker_id: str | None = None,
        poll_interval: float = 2.0,
        lease_seconds: int = 300,
        stale_check_interval: float = 60.0,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.poll_interval = poll_interval
        self.lease_seconds = lease_seconds
        self.stale_check_interval = stale_check_interval
        self._session_factory = session_factory or SessionLocal
        self._shutdown_requested = False
        self._last_stale_check = 0.0

    def request_shutdown(self) -> None:
        """Signal the worker to gracefully complete current task and stop."""
        logger.info("Worker %s: shutdown requested, finishing active operations...", self.worker_id)
        self._shutdown_requested = True

    def _setup_signal_handlers(self) -> None:
        """Register graceful shutdown hooks for SIGINT and SIGTERM."""
        try:
            signal.signal(signal.SIGINT, lambda s, f: self.request_shutdown())
            signal.signal(signal.SIGTERM, lambda s, f: self.request_shutdown())
        except (ValueError, AttributeError):
            # Signals might not be interceptable in non-main threads or some environments
            pass

    def run_once(self) -> bool:
        """
        Attempt to claim and process exactly one task.

        Returns:
            True if a task was processed, False if queue was empty.
        """
        # Periodic watchdog: recover tasks abandoned by crashed workers
        now_ts = time.time()
        if now_ts - self._last_stale_check >= self.stale_check_interval:
            self._recover_stale_tasks()
            self._last_stale_check = now_ts

        db = self._session_factory()
        try:
            queue_service = TaskQueueService(db)
            task = queue_service.claim_task(
                worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
            )
            if task is None:
                return False

            task_id = task.id
            task_type = task.task_type
        finally:
            db.close()

        # Execute task with a fresh isolated DB session
        self._execute_claimed_task(task_id, task_type)
        return True

    def _execute_claimed_task(self, task_id: uuid.UUID, task_type: str) -> None:
        """Execute a claimed task inside an isolated try/except block."""
        handler = TASK_HANDLERS.get(task_type)
        if handler is None:
            logger.error("No handler registered for task type: %s", task_type)
            db = self._session_factory()
            try:
                TaskQueueService(db).fail_task(
                    task_id=task_id,
                    worker_id=self.worker_id,
                    error_message=f"No handler registered for task type '{task_type}'",
                    retry=False,
                )
            finally:
                db.close()
            return

        db = self._session_factory()
        try:
            task = db.get(Task, task_id)
            if task is None:
                logger.error("Task %s disappeared before execution", task_id)
                return

            start_time = time.perf_counter()
            result = handler(task, db)
            duration = time.perf_counter() - start_time

            TaskQueueService(db).complete_task(
                task_id=task_id,
                worker_id=self.worker_id,
                result=result,
            )
            logger.info(
                "Worker %s successfully completed task_id=%s type=%s in %.2fs",
                self.worker_id,
                task_id,
                task_type,
                duration,
            )
        except Exception as exc:
            logger.exception(
                "Worker %s: error executing task_id=%s type=%s: %s",
                self.worker_id,
                task_id,
                task_type,
                exc,
            )
            try:
                # Mark failed with bounded exponential backoff
                TaskQueueService(db).fail_task(
                    task_id=task_id,
                    worker_id=self.worker_id,
                    error_message=str(exc),
                    retry=True,
                )
            except Exception as fail_exc:
                logger.error("Failed to record task failure for %s: %s", task_id, fail_exc)
        finally:
            db.close()

    def _recover_stale_tasks(self) -> None:
        """Run watchdog check for tasks with expired leases."""
        db = self._session_factory()
        try:
            recovered = TaskQueueService(db).recover_stale_tasks()
            if recovered:
                logger.warning(
                    "Worker %s watchdog recovered %d stale task(s)",
                    self.worker_id,
                    len(recovered),
                )
        except Exception as exc:
            logger.warning("Worker %s watchdog check failed: %s", self.worker_id, exc)
        finally:
            db.close()

    def run(self) -> None:
        """Main polling loop. Runs until shutdown is requested."""
        logger.info(
            "Worker %s started (poll_interval=%.1fs, lease_seconds=%ds)",
            self.worker_id,
            self.poll_interval,
            self.lease_seconds,
        )
        self._setup_signal_handlers()

        while not self._shutdown_requested:
            try:
                processed = self.run_once()
                if not processed:
                    # Responsive sleep in slices so SIGINT/SIGTERM exits promptly
                    sleep_remaining = self.poll_interval
                    while sleep_remaining > 0 and not self._shutdown_requested:
                        slice_time = min(0.5, sleep_remaining)
                        time.sleep(slice_time)
                        sleep_remaining -= slice_time
            except Exception as loop_exc:
                logger.error("Worker %s encountered loop exception: %s", self.worker_id, loop_exc)
                time.sleep(1.0)

        logger.info("Worker %s stopped cleanly.", self.worker_id)
