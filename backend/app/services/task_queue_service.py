"""
Task queue service for PostgreSQL-backed durable background jobs.

Provides:
  - Enqueueing tasks with payload validation and optional delay.
  - Concurrent-safe atomic claiming using SELECT ... FOR UPDATE SKIP LOCKED.
  - Worker lease renewal (heartbeat) and lease timeout enforcement.
  - Execution completion and exponential backoff retry scheduling.
  - Stale worker crash recovery (reclaims tasks when worker lease expires).
  - User-scoped access checks.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task

logger = logging.getLogger(__name__)


class TaskQueueError(Exception):
    """Base exception for task queue service errors."""


class TaskNotFoundError(TaskQueueError):
    """Raised when a requested task does not exist or user lacks access."""


class InvalidTaskTransitionError(TaskQueueError):
    """Raised when an illegal status transition is attempted."""


class TaskLeaseLostError(TaskQueueError):
    """Raised when a worker attempts to update a task whose lease expired or belongs to another worker."""


class TaskQueueService:
    """Service managing PostgreSQL-backed task queue lifecycle and worker leases."""

    def __init__(self, db: Session, user_id: uuid.UUID | str | None = None) -> None:
        self._db = db
        self._user_id = uuid.UUID(str(user_id)) if user_id is not None else None

    # ── Enqueueing ─────────────────────────────────────────────────────────

    def enqueue(
        self,
        task_type: str,
        payload: dict[str, Any],
        user_id: uuid.UUID | str | None = None,
        max_attempts: int = 3,
        delay_seconds: int = 0,
        idempotency_key: str | None = None,
    ) -> Task:
        """
        Enqueue a new task for background execution.

        Args:
            task_type: One of TASK_TYPE_VALUES ('scrape', 'scoring', 'bulk_score', etc.).
            payload: JSON-serializable parameters (must not contain secrets/passwords).
            user_id: Optional user owner (defaults to session user_id).
            max_attempts: Total allowed attempts before terminal failure.
            delay_seconds: Delay before task becomes available for claiming.
            idempotency_key: Optional key inside payload to prevent duplicate pending tasks.

        Returns:
            The created Task ORM instance in 'queued' status.
        """
        resolved_user_id = (
            uuid.UUID(str(user_id)) if user_id is not None else self._user_id
        )

        now = datetime.now(UTC)
        available_at = now + timedelta(seconds=max(0, delay_seconds))

        # Idempotency check: if an identical task is already queued or running, return it
        if idempotency_key is not None:
            existing = self._find_existing_idempotent_task(
                task_type=task_type,
                resolved_user_id=resolved_user_id,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                logger.info(
                    "enqueue: idempotent deduplication matched existing task_id=%s (type=%s, status=%s)",
                    existing.id,
                    task_type,
                    existing.status,
                )
                return existing

        task = Task(
            id=uuid.uuid4(),
            task_type=task_type,
            status="queued",
            user_id=resolved_user_id,
            payload=payload,
            max_attempts=max_attempts,
            attempt_count=0,
            available_at=available_at,
            created_at=now,
        )
        self._db.add(task)
        self._db.commit()
        self._db.refresh(task)
        logger.info(
            "enqueue: task enqueued id=%s type=%s user_id=%s available_at=%s",
            task.id,
            task.task_type,
            task.user_id,
            task.available_at,
        )
        return task

    # ── Worker Claiming (Atomic & Concurrency-Safe) ─────────────────────────

    def claim_task(
        self,
        worker_id: str,
        lease_seconds: int = 300,
        task_types: list[str] | None = None,
    ) -> Task | None:
        """
        Atomically claim the highest-priority eligible queued task using FOR UPDATE SKIP LOCKED.

        Safe across multiple concurrent worker instances and processes.

        Args:
            worker_id: Unique identifier of claiming worker process.
            lease_seconds: Initial lease duration before crash detection considers it stale.
            task_types: Optional list of task types this worker accepts.

        Returns:
            The claimed Task in 'running' status, or None if no tasks are eligible.
        """
        now = datetime.now(UTC)
        lease_timeout_at = now + timedelta(seconds=lease_seconds)

        is_pg = (
            self._db.bind is not None
            and getattr(self._db.bind.dialect, "name", "") == "postgresql"
        )

        query = (
            select(Task)
            .where(
                Task.status == "queued",
                Task.available_at <= now,
            )
            .order_by(Task.available_at.asc(), Task.created_at.asc())
            .limit(1)
        )

        if task_types:
            query = query.where(Task.task_type.in_(task_types))

        if is_pg:
            # PostgreSQL: FOR UPDATE SKIP LOCKED guarantees zero contention blocking
            query = query.with_for_update(skip_locked=True)
        else:
            # Fallback for non-Postgres test environments
            query = query.with_for_update()

        task = self._db.execute(query).scalar_one_or_none()
        if task is None:
            return None

        # Transition status: queued -> running
        task.status = "running"
        task.worker_id = worker_id
        task.attempt_count += 1
        task.started_at = now
        task.lease_timeout_at = lease_timeout_at
        task.error_message = None

        self._db.commit()
        self._db.refresh(task)

        logger.info(
            "claim_task: worker=%s claimed task_id=%s type=%s attempt=%d/%d lease_until=%s",
            worker_id,
            task.id,
            task.task_type,
            task.attempt_count,
            task.max_attempts,
            task.lease_timeout_at,
        )
        return task

    # ── Heartbeat & Lease Renewal ──────────────────────────────────────────

    def heartbeat(
        self,
        task_id: uuid.UUID,
        worker_id: str,
        extend_seconds: int = 300,
    ) -> bool:
        """
        Renew worker lease for an ongoing task to prevent premature crash recovery.

        Verifies worker_id ownership and that the task is currently 'running'.

        Returns:
            True if lease was extended, False if lease was lost.
        """
        task = self._db.get(Task, task_id)
        if task is None:
            return False

        if task.status != "running" or task.worker_id != worker_id:
            logger.warning(
                "heartbeat rejected: task_id=%s worker=%s current_worker=%s status=%s",
                task_id,
                worker_id,
                task.worker_id,
                task.status,
            )
            return False

        task.lease_timeout_at = datetime.now(UTC) + timedelta(seconds=extend_seconds)
        self._db.commit()
        return True

    # ── Completion & Terminal States ───────────────────────────────────────

    def complete_task(
        self,
        task_id: uuid.UUID,
        worker_id: str,
        result: dict[str, Any] | None = None,
    ) -> Task:
        """
        Mark a running task as succeeded.

        Verifies that worker_id still owns the active lease.
        """
        task = self._get_task_for_worker_update(task_id, worker_id)

        now = datetime.now(UTC)
        task.status = "succeeded"
        task.result = result
        task.completed_at = now
        task.lease_timeout_at = None

        self._db.commit()
        self._db.refresh(task)

        logger.info(
            "complete_task: task_id=%s succeeded worker=%s duration=%.2fs",
            task.id,
            worker_id,
            (now - task.started_at).total_seconds() if task.started_at else 0.0,
        )
        return task

    def fail_task(
        self,
        task_id: uuid.UUID,
        worker_id: str,
        error_message: str,
        retry: bool = True,
        backoff_base_seconds: int = 30,
    ) -> Task:
        """
        Handle task failure with bounded exponential backoff retries.

        If attempts remain and retry=True:
            Re-queues with exponential backoff: delay = backoff_base * (2 ** (attempt - 1)).
        Else:
            Marks task as terminal 'failed'.
        """
        task = self._get_task_for_worker_update(task_id, worker_id)

        now = datetime.now(UTC)
        safe_error = (error_message or "Unknown failure")[:1000]
        task.error_message = safe_error

        should_retry = retry and (task.attempt_count < task.max_attempts)

        if should_retry:
            backoff_delay = backoff_base_seconds * (2 ** (task.attempt_count - 1))
            task.status = "queued"
            task.available_at = now + timedelta(seconds=backoff_delay)
            task.worker_id = None
            task.lease_timeout_at = None
            task.started_at = None
            logger.warning(
                "fail_task: task_id=%s failed (attempt %d/%d). Retrying in %ds: %s",
                task.id,
                task.attempt_count,
                task.max_attempts,
                backoff_delay,
                safe_error,
            )
        else:
            task.status = "failed"
            task.completed_at = now
            task.lease_timeout_at = None
            logger.error(
                "fail_task: task_id=%s failed terminally after %d attempts: %s",
                task.id,
                task.attempt_count,
                safe_error,
            )

        self._db.commit()
        self._db.refresh(task)
        return task

    def cancel_task(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Task:
        """Cancel a queued task before execution begins."""
        task = self.get_task(task_id, user_id=user_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} not found")

        if task.status != "queued":
            raise InvalidTaskTransitionError(
                f"Cannot cancel task {task_id} in status '{task.status}'. Only 'queued' tasks can be cancelled."
            )

        task.status = "cancelled"
        task.completed_at = datetime.now(UTC)
        task.lease_timeout_at = None

        self._db.commit()
        self._db.refresh(task)
        return task

    # ── Crash Recovery ─────────────────────────────────────────────────────

    def recover_stale_tasks(
        self,
        lease_grace_seconds: int = 0,
        backoff_base_seconds: int = 30,
    ) -> list[Task]:
        """
        Recover abandoned tasks where a worker died or timed out while holding lease.

        Finds running tasks where lease_timeout_at + grace < now().
        Re-queues tasks with attempts remaining; marks exhausted tasks as failed.
        """
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=lease_grace_seconds)

        stale_stmt = (
            select(Task)
            .where(
                Task.status == "running",
                Task.lease_timeout_at.is_not(None),
                Task.lease_timeout_at <= cutoff,
            )
        )
        stale_tasks = list(self._db.execute(stale_stmt).scalars().all())

        recovered: list[Task] = []
        for task in stale_tasks:
            prev_worker = task.worker_id
            safe_msg = f"Worker lease expired ({prev_worker}); recovered by watchdog."
            task.error_message = safe_msg

            if task.attempt_count < task.max_attempts:
                delay = backoff_base_seconds * (2 ** (task.attempt_count - 1))
                task.status = "queued"
                task.available_at = now + timedelta(seconds=delay)
                task.worker_id = None
                task.lease_timeout_at = None
                task.started_at = None
                logger.warning(
                    "recover_stale_tasks: recovered task_id=%s attempt=%d/%d, re-queued with %ds delay",
                    task.id,
                    task.attempt_count,
                    task.max_attempts,
                    delay,
                )
            else:
                task.status = "failed"
                task.completed_at = now
                task.lease_timeout_at = None
                logger.error(
                    "recover_stale_tasks: task_id=%s failed terminally on lease expiration",
                    task.id,
                )
            recovered.append(task)

        if recovered:
            self._db.commit()
            for t in recovered:
                self._db.refresh(t)

        return recovered

    # ── Read / Status Inspection ───────────────────────────────────────────

    def get_task(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Task | None:
        """
        Fetch a task by ID with user ownership authorization.

        If user_id is provided, only returns the task if user owns it.
        """
        task = self._db.get(Task, task_id)
        if task is None:
            return None

        uid = user_id or self._user_id
        if uid is not None and task.user_id is not None and task.user_id != uid:
            return None

        return task

    def list_tasks(
        self,
        user_id: uuid.UUID | None = None,
        task_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Task]:
        """List tasks for operational inspection or user dashboard."""
        query = select(Task).order_by(Task.created_at.desc()).limit(limit)

        uid = user_id or self._user_id
        if uid is not None:
            query = query.where(Task.user_id == uid)

        if task_type:
            query = query.where(Task.task_type == task_type)

        if status:
            query = query.where(Task.status == status)

        return list(self._db.execute(query).scalars().all())

    # ── Internal Helpers ───────────────────────────────────────────────────

    def _get_task_for_worker_update(self, task_id: uuid.UUID, worker_id: str) -> Task:
        """Fetch task and verify caller worker owns the active lease."""
        task = self._db.get(Task, task_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} not found")

        if task.status != "running":
            raise InvalidTaskTransitionError(
                f"Task {task_id} is in status '{task.status}', expected 'running'"
            )

        if task.worker_id != worker_id:
            raise TaskLeaseLostError(
                f"Worker '{worker_id}' does not own active lease on task {task_id} (owned by '{task.worker_id}')"
            )

        return task

    def _find_existing_idempotent_task(
        self,
        task_type: str,
        resolved_user_id: uuid.UUID | None,
        idempotency_key: str,
    ) -> Task | None:
        """Check if an active/queued task with same idempotency key already exists."""
        query = select(Task).where(
            Task.task_type == task_type,
            Task.status.in_(["queued", "running"]),
            Task.payload.contains({"idempotency_key": idempotency_key}),
        )
        if resolved_user_id is not None:
            query = query.where(Task.user_id == resolved_user_id)

        return self._db.execute(query.limit(1)).scalar_one_or_none()
