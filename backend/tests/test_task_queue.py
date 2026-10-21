"""
Unit and integration tests for PostgreSQL Task Queue and Background Worker (Phase 1).
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.task_queue_service import (
    InvalidTaskTransitionError,
    TaskLeaseLostError,
    TaskQueueService,
)
from app.worker.worker import BackgroundWorker
from tests.conftest import needs_db

pytestmark = needs_db


# ── Fixtures & Setup ─────────────────────────────────────────────────────────

@pytest.fixture()
def second_user(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"user2-{uuid.uuid4().hex[:8]}@example.com",
        name="Second Test User",
        password_hash="test-password-hash",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Test Task Queue Basics ──────────────────────────────────────────────────

class TestTaskQueueBasics:
    def test_enqueue_task_creation(self, db: Session, sample_user: User) -> None:
        service = TaskQueueService(db, user_id=sample_user.id)
        task = service.enqueue(
            task_type="scrape",
            payload={"auto_score": True},
            user_id=sample_user.id,
            max_attempts=4,
        )

        assert task.id is not None
        assert task.task_type == "scrape"
        assert task.status == "queued"
        assert task.user_id == sample_user.id
        assert task.payload == {"auto_score": True}
        assert task.attempt_count == 0
        assert task.max_attempts == 4
        assert task.available_at <= datetime.now(UTC)
        assert task.worker_id is None
        assert task.started_at is None
        assert task.completed_at is None

    def test_enqueue_with_delay(self, db: Session, sample_user: User) -> None:
        service = TaskQueueService(db, user_id=sample_user.id)
        now = datetime.now(UTC)
        task = service.enqueue(
            task_type="scoring",
            payload={"job_ids": ["123"]},
            delay_seconds=60,
        )
        assert task.available_at >= now + timedelta(seconds=55)

    def test_idempotent_enqueue(self, db: Session, sample_user: User) -> None:
        service = TaskQueueService(db, user_id=sample_user.id)
        payload1 = {"idempotency_key": "sync-2026-10-09", "val": 1}
        payload2 = {"idempotency_key": "sync-2026-10-09", "val": 2}

        task1 = service.enqueue("scrape", payload1, idempotency_key="sync-2026-10-09")
        task2 = service.enqueue("scrape", payload2, idempotency_key="sync-2026-10-09")

        assert task1.id == task2.id

    def test_cancel_queued_task(self, db: Session, sample_user: User) -> None:
        service = TaskQueueService(db, user_id=sample_user.id)
        task = service.enqueue("scrape", {})
        cancelled = service.cancel_task(task.id, user_id=sample_user.id)

        assert cancelled.status == "cancelled"
        assert cancelled.completed_at is not None

    def test_cannot_cancel_running_task(self, db: Session, sample_user: User) -> None:
        service = TaskQueueService(db, user_id=sample_user.id)
        task = service.enqueue("scrape", {})
        claimed = service.claim_task(worker_id="worker-1")
        assert claimed is not None

        with pytest.raises(InvalidTaskTransitionError):
            service.cancel_task(task.id, user_id=sample_user.id)


# ── Test Atomic Claiming & Concurrency ──────────────────────────────────────

class TestAtomicClaimingAndLeases:
    def test_single_worker_claim(self, db: Session) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {"foo": "bar"})

        claimed = service.claim_task(worker_id="worker-alpha", lease_seconds=120)
        assert claimed is not None
        assert claimed.id == task.id
        assert claimed.status == "running"
        assert claimed.worker_id == "worker-alpha"
        assert claimed.attempt_count == 1
        assert claimed.started_at is not None
        assert claimed.lease_timeout_at is not None
        assert claimed.lease_timeout_at > datetime.now(UTC)

        # Immediate second claim sees no available tasks
        second_claim = service.claim_task(worker_id="worker-beta")
        assert second_claim is None

    def test_future_task_cannot_be_claimed(self, db: Session) -> None:
        service = TaskQueueService(db)
        service.enqueue("scrape", {}, delay_seconds=300)

        claimed = service.claim_task(worker_id="worker-1")
        assert claimed is None

    def test_filter_by_task_type(self, db: Session) -> None:
        service = TaskQueueService(db)
        service.enqueue("scoring", {})
        service.enqueue("scrape", {})

        # Worker only claims 'scrape'
        claimed = service.claim_task(worker_id="worker-1", task_types=["scrape"])
        assert claimed is not None
        assert claimed.task_type == "scrape"

    def test_heartbeat_renews_lease(self, db: Session) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {})
        claimed = service.claim_task("worker-1", lease_seconds=60)
        assert claimed is not None

        old_lease = claimed.lease_timeout_at
        time.sleep(0.05)
        success = service.heartbeat(task.id, worker_id="worker-1", extend_seconds=300)
        assert success is True

        db.refresh(claimed)
        assert old_lease is not None
        assert claimed.lease_timeout_at is not None
        assert claimed.lease_timeout_at > old_lease


    def test_stale_worker_cannot_heartbeat_or_complete(self, db: Session) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {})
        service.claim_task("worker-1")

        # Wrong worker attempts heartbeat
        assert service.heartbeat(task.id, "worker-impostor") is False

        # Wrong worker attempts completion
        with pytest.raises(TaskLeaseLostError):
            service.complete_task(task.id, "worker-impostor")


# ── Test Completion & Retry ─────────────────────────────────────────────────

class TestCompletionAndRetry:
    def test_complete_task_success(self, db: Session) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {})
        service.claim_task("worker-1")

        completed = service.complete_task(
            task.id,
            worker_id="worker-1",
            result={"found": 12, "new": 5},
        )
        assert completed.status == "succeeded"
        assert completed.result == {"found": 12, "new": 5}
        assert completed.completed_at is not None
        assert completed.lease_timeout_at is None

    def test_fail_task_with_retry_backoff(self, db: Session) -> None:
        service = TaskQueueService(db)
        now = datetime.now(UTC)
        task = service.enqueue("scrape", {}, max_attempts=3)
        service.claim_task("worker-1")

        failed = service.fail_task(
            task.id,
            worker_id="worker-1",
            error_message="Network glitch",
            retry=True,
            backoff_base_seconds=10,
        )

        assert failed.status == "queued"
        assert failed.worker_id is None
        assert failed.lease_timeout_at is None
        assert failed.attempt_count == 1
        assert failed.error_message == "Network glitch"
        # 10 * 2^(1-1) = 10s delay
        assert failed.available_at >= now + timedelta(seconds=9)

    def test_fail_task_terminal_when_attempts_exhausted(self, db: Session) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {}, max_attempts=1)
        service.claim_task("worker-1")

        failed = service.fail_task(
            task.id,
            worker_id="worker-1",
            error_message="Fatal error",
            retry=True,
        )
        assert failed.status == "failed"
        assert failed.completed_at is not None
        assert failed.attempt_count == 1


# ── Test Watchdog & Stale Task Recovery ─────────────────────────────────────

class TestWatchdogRecovery:
    def test_recover_stale_task(self, db: Session) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {}, max_attempts=3)
        service.claim_task("crashed-worker", lease_seconds=1)

        # Manually expire lease in DB
        task.lease_timeout_at = datetime.now(UTC) - timedelta(seconds=10)
        db.commit()

        recovered = service.recover_stale_tasks(lease_grace_seconds=0, backoff_base_seconds=5)
        assert len(recovered) == 1
        assert recovered[0].id == task.id
        assert recovered[0].status == "queued"
        assert "Worker lease expired" in (recovered[0].error_message or "")

    def test_recover_stale_task_terminal_when_exhausted(self, db: Session) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {}, max_attempts=1)
        service.claim_task("crashed-worker", lease_seconds=1)

        task.lease_timeout_at = datetime.now(UTC) - timedelta(seconds=10)
        db.commit()

        recovered = service.recover_stale_tasks(lease_grace_seconds=0)
        assert len(recovered) == 1
        assert recovered[0].status == "failed"


class _NonClosingSessionWrapper:
    """Wrapper around test fixture session so worker.run_once() does not close it."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)

    def close(self) -> None:
        pass


# ── Test Background Worker Lifecycle ────────────────────────────────────────

class TestWorkerLifecycle:
    def test_worker_run_once_success(self, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {"auto_score": False})

        # Mock handle_scrape
        from app.worker import handlers
        mock_handler = MagicMock(return_value={"total_new": 3, "runs": []})
        monkeypatch.setitem(handlers.TASK_HANDLERS, "scrape", mock_handler)

        worker = BackgroundWorker(
            worker_id="test-worker-1",
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )
        processed = worker.run_once()
        assert processed is True
        mock_handler.assert_called_once()

        db.refresh(task)
        assert task.status == "succeeded"
        assert task.result == {"total_new": 3, "runs": []}

    def test_worker_unknown_task_fails(self, db: Session) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("unregistered_type", {})

        worker = BackgroundWorker(
            worker_id="test-worker-1",
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )
        processed = worker.run_once()
        assert processed is True

        db.refresh(task)
        assert task.status == "failed"
        assert "No handler registered" in (task.error_message or "")

    def test_worker_handler_exception_retries(self, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {}, max_attempts=3)

        from app.worker import handlers
        failing_handler = MagicMock(side_effect=RuntimeError("Simulated scraper crash"))
        monkeypatch.setitem(handlers.TASK_HANDLERS, "scrape", failing_handler)

        worker = BackgroundWorker(
            worker_id="test-worker-1",
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )
        processed = worker.run_once()
        assert processed is True

        db.refresh(task)
        assert task.status == "queued"
        assert "Simulated scraper crash" in (task.error_message or "")
        assert task.attempt_count == 1


# ── Test Background Worker Drain Mode (Phase 1) ─────────────────────────────

class TestWorkerDrainMode:
    def test_drain_empty_queue_returns_zero(self, db: Session) -> None:
        """When queue has no eligible tasks, run_drain returns 0 and does not error."""
        worker = BackgroundWorker(
            worker_id="test-drain-worker-empty",
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )
        count = worker.run_drain(max_duration_seconds=60.0)
        assert count == 0

    def test_drain_single_task_success(
        self,
        db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """One available task is processed successfully to completion."""
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {"auto_score": False})

        from app.worker import handlers
        mock_handler = MagicMock(return_value={"total_new": 1, "runs": []})
        monkeypatch.setitem(handlers.TASK_HANDLERS, "scrape", mock_handler)

        worker = BackgroundWorker(
            worker_id="test-drain-worker-single",
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )
        count = worker.run_drain(max_duration_seconds=60.0)
        assert count == 1
        mock_handler.assert_called_once()

        db.refresh(task)
        assert task.status == "succeeded"
        assert task.result == {"total_new": 1, "runs": []}

    def test_drain_multiple_tasks(
        self,
        db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Multiple eligible tasks are processed sequentially in a single drain run."""
        service = TaskQueueService(db)
        task1 = service.enqueue("scrape", {"batch": 1})
        task2 = service.enqueue("scrape", {"batch": 2})
        task3 = service.enqueue("scrape", {"batch": 3})

        from app.worker import handlers
        call_order: list[uuid.UUID] = []

        def _track_handler(task_obj: Any, session: Session) -> dict[str, Any]:
            call_order.append(task_obj.id)
            return {"batch": task_obj.payload.get("batch")}

        monkeypatch.setitem(handlers.TASK_HANDLERS, "scrape", _track_handler)

        worker = BackgroundWorker(
            worker_id="test-drain-worker-multi",
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )
        count = worker.run_drain(max_duration_seconds=60.0)
        assert count == 3
        assert len(call_order) == 3

        for t in (task1, task2, task3):
            db.refresh(t)
            assert t.status == "succeeded"

    def test_drain_task_failure_follows_retry_semantics_and_does_not_loop(
        self,
        db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        A failing task follows exponential backoff retry semantics.
        The worker reschedules available_at into the future and does not loop infinitely.
        The task remains in 'queued' status (not completed).
        """
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {}, max_attempts=3)

        from app.worker import handlers
        mock_failing = MagicMock(side_effect=RuntimeError("Handler failure"))
        monkeypatch.setitem(handlers.TASK_HANDLERS, "scrape", mock_failing)

        worker = BackgroundWorker(
            worker_id="test-drain-worker-fail",
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )
        count = worker.run_drain(max_duration_seconds=60.0)

        # Processed attempt 1, then queue had no more immediately eligible tasks
        assert count == 1
        mock_failing.assert_called_once()

        db.refresh(task)
        assert task.status == "queued"
        assert task.attempt_count == 1
        assert task.available_at > datetime.now(UTC)
        assert "Handler failure" in (task.error_message or "")

    def test_drain_deadline_stops_claiming_new_tasks_safely(
        self,
        db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Deadline prevents claiming additional tasks without interrupting the active task.
        In-flight task completes cleanly, subsequent tasks remain queued.
        """
        service = TaskQueueService(db)
        task1 = service.enqueue("scrape", {"step": 1})
        task2 = service.enqueue("scrape", {"step": 2})

        from app.worker import handlers

        def _slow_handler(task_obj: Any, session: Session) -> dict[str, Any]:
            time.sleep(0.05)
            return {"step": task_obj.payload.get("step")}

        monkeypatch.setitem(handlers.TASK_HANDLERS, "scrape", _slow_handler)

        worker = BackgroundWorker(
            worker_id="test-drain-worker-deadline",
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )

        # Deadline of 0.01 seconds guarantees task 1 exceeds it, preventing task 2 from being claimed
        count = worker.run_drain(max_duration_seconds=0.01)
        assert count == 1

        db.refresh(task1)
        assert task1.status == "succeeded"

        db.refresh(task2)
        assert task2.status == "queued"
        assert task2.attempt_count == 0

    def test_drain_shutdown_request_stops_claiming(
        self,
        db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Shutdown signal stops claiming new work after current task completes."""
        service = TaskQueueService(db)
        task1 = service.enqueue("scrape", {"n": 1})
        task2 = service.enqueue("scrape", {"n": 2})

        from app.worker import handlers
        worker = BackgroundWorker(
            worker_id="test-drain-worker-sig",
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )

        def _handler_triggering_shutdown(task_obj: Any, session: Session) -> dict[str, Any]:
            worker.request_shutdown()
            return {"n": task_obj.payload.get("n")}

        monkeypatch.setitem(handlers.TASK_HANDLERS, "scrape", _handler_triggering_shutdown)

        count = worker.run_drain(max_duration_seconds=60.0)
        assert count == 1

        db.refresh(task1)
        assert task1.status == "succeeded"

        db.refresh(task2)
        assert task2.status == "queued"

    def test_worker_main_drain_empty_queue_exits_zero(
        self,
        db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CLI with --drain exits with code 0 on empty queue."""
        from app.worker import main

        monkeypatch.setattr(
            "app.worker.main.BackgroundWorker",
            lambda **kwargs: BackgroundWorker(
                session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
                **kwargs,
            ),
        )

        with pytest.raises(SystemExit) as exc_info:
            main.main(["--drain", "--max-duration-seconds", "10"])
        assert exc_info.value.code == 0

    def test_worker_main_once_flag_exit_codes_preserved(
        self,
        db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Existing --once behavior is preserved: exits 1 when empty, exits 0 when task processed."""
        from app.worker import main

        monkeypatch.setattr(
            "app.worker.main.BackgroundWorker",
            lambda **kwargs: BackgroundWorker(
                session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
                **kwargs,
            ),
        )

        # 1. Empty queue exits with 1
        with pytest.raises(SystemExit) as exc_empty:
            main.main(["--once"])
        assert exc_empty.value.code == 1

        # 2. Populated queue exits with 0
        service = TaskQueueService(db)
        service.enqueue("scrape", {})

        from app.worker import handlers
        monkeypatch.setitem(
            handlers.TASK_HANDLERS, "scrape", lambda t, s: {"status": "ok"}
        )

        with pytest.raises(SystemExit) as exc_task:
            main.main(["--once"])
        assert exc_task.value.code == 0

    def test_worker_main_database_error_exits_one_and_sanitizes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Database connection or initialization failure logs sanitized error and exits with code 1."""
        import logging

        from app.worker import main

        sensitive_error = (
            "OperationalError: password authentication failed for user "
            "postgresql://db_user:SUPER_SECRET_PASSWORD@db.neon.tech/neondb"
        )

        def _crashing_drain(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError(sensitive_error)

        monkeypatch.setattr(
            "app.worker.main.BackgroundWorker.run_drain",
            _crashing_drain,
        )

        with (
            caplog.at_level(logging.CRITICAL, logger="app.worker"),
            pytest.raises(SystemExit) as exc_info,
        ):
            main.main(["--drain"])

        assert exc_info.value.code == 1
        assert "SUPER_SECRET_PASSWORD" not in caplog.text
        assert "postgresql://db_user:***@db.neon.tech/neondb" in caplog.text

    def test_sanitize_error_message(self) -> None:
        """Sanitizer helper redacts database credentials and token patterns."""
        from app.worker.main import sanitize_error_message

        raw = (
            "FATAL: connection to postgresql://admin:MyPass123!@ep-xyz.aws.neon.tech/prod_db "
            "failed with token=eyJhbGciOiJIUzI1NiIsIn and password=super_secret_val"
        )
        sanitized = sanitize_error_message(raw)
        assert "MyPass123!" not in sanitized
        assert "postgresql://admin:***@ep-xyz.aws.neon.tech/prod_db" in sanitized
        assert "password=***" in sanitized
        assert "token=***" in sanitized


# ── Test API Endpoints ──────────────────────────────────────────────────────

class TestTaskAPI:
    def test_get_task_owner_access(
        self,
        db: Session,
        sample_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        service = TaskQueueService(db, user_id=sample_user.id)
        task = service.enqueue("scrape", {"test": True}, user_id=sample_user.id)

        resp = client.get(f"/api/tasks/{task.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == str(task.id)
        assert data["task_type"] == "scrape"
        assert data["status"] == "queued"

    def test_get_task_forbidden_for_other_user(
        self,
        db: Session,
        sample_user: User,
        second_user: User,
        client: TestClient,
    ) -> None:
        from app.core.security import create_access_token

        # Task owned by user 1
        service = TaskQueueService(db, user_id=sample_user.id)
        task = service.enqueue("scrape", {}, user_id=sample_user.id)

        # Request made by user 2
        token2 = create_access_token({"sub": str(second_user.id), "email": second_user.email})
        resp = client.get(f"/api/tasks/{task.id}", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 404

    def test_list_tasks(
        self,
        db: Session,
        sample_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        service = TaskQueueService(db, user_id=sample_user.id)
        service.enqueue("scrape", {}, user_id=sample_user.id)
        service.enqueue("scoring", {}, user_id=sample_user.id)

        resp = client.get("/api/tasks", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 2

    def test_cancel_task_api(
        self,
        db: Session,
        sample_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        service = TaskQueueService(db, user_id=sample_user.id)
        task = service.enqueue("scrape", {}, user_id=sample_user.id)

        resp = client.post(f"/api/tasks/{task.id}/cancel", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    def test_get_system_owned_task_forbidden_for_user(
        self,
        db: Session,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        """Authenticated user cannot inspect a system-owned task (returns 404)."""
        service = TaskQueueService(db)
        sys_task = service.enqueue("scrape", {"internal": True}, user_id=None)

        resp = client.get(f"/api/tasks/{sys_task.id}", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    def test_cancel_system_owned_task_forbidden_for_user(
        self,
        db: Session,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        """Authenticated user cannot cancel a system-owned task (returns 404)."""
        service = TaskQueueService(db)
        sys_task = service.enqueue("scrape", {"internal": True}, user_id=None)

        resp = client.post(f"/api/tasks/{sys_task.id}/cancel", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

        # Task in DB remains queued
        db.refresh(sys_task)
        assert sys_task.status == "queued"

    def test_cancel_other_user_task_forbidden(
        self,
        db: Session,
        sample_user: User,
        second_user: User,
        client: TestClient,
    ) -> None:
        """User B cannot cancel User A's task (returns 404)."""
        from app.core.security import create_access_token

        # User A's task
        service = TaskQueueService(db, user_id=sample_user.id)
        task = service.enqueue("scrape", {}, user_id=sample_user.id)

        # User B attempts to cancel
        token2 = create_access_token({"sub": str(second_user.id), "email": second_user.email})
        resp = client.post(
            f"/api/tasks/{task.id}/cancel",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

        # Task remains queued
        db.refresh(task)
        assert task.status == "queued"

    def test_list_tasks_excludes_system_and_other_user_tasks(
        self,
        db: Session,
        sample_user: User,
        second_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        """GET /api/tasks only returns tasks owned by the requesting user."""
        service_a = TaskQueueService(db, user_id=sample_user.id)
        task_a = service_a.enqueue("scrape", {"owner": "a"}, user_id=sample_user.id)

        service_b = TaskQueueService(db, user_id=second_user.id)
        service_b.enqueue("scrape", {"owner": "b"}, user_id=second_user.id)

        service_sys = TaskQueueService(db)
        service_sys.enqueue("scrape", {"owner": "sys"}, user_id=None)

        resp = client.get("/api/tasks", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["data"]
        item_ids = [it["id"] for it in items]
        assert str(task_a.id) in item_ids
        for it in items:
            assert it["user_id"] == str(sample_user.id)

    def test_internal_worker_can_process_system_owned_task(
        self,
        db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Internal worker processes system-owned tasks normally."""
        from typing import cast

        from app.models.task import Task
        from app.worker.handlers import TASK_HANDLERS
        from app.worker.worker import BackgroundWorker

        def _mock_handler(task: Task, session: Session) -> dict[str, Any]:
            return {"system_job": "completed"}

        monkeypatch.setitem(TASK_HANDLERS, "scrape", _mock_handler)

        service = TaskQueueService(db)
        sys_task = service.enqueue("scrape", {"cron": True}, user_id=None)
        assert sys_task.user_id is None

        # Internal service query can inspect system task
        inspected = service.get_task(sys_task.id)
        assert inspected is not None
        assert inspected.id == sys_task.id

        worker = BackgroundWorker(
            worker_id="system-worker-1",
            lease_seconds=30,
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )
        processed = worker.run_once()
        assert processed is True

        db.refresh(sys_task)
        assert sys_task.status == "succeeded"
        assert sys_task.result == {"system_job": "completed"}

    def test_enqueue_scraper_api(
        self,
        db: Session,
        sample_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        resp = client.post("/api/scraper/enqueue", headers=auth_headers)
        assert resp.status_code == 202
        data = resp.json()["data"]
        assert data["task_type"] == "scrape"
        assert data["status"] == "queued"


# ── Test Worker Heartbeat Regression & Stale Fencing ────────────────────────

class TestWorkerHeartbeatRegression:
    def test_task_running_longer_than_lease_renews_heartbeat(
        self,
        db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Simulate a handler executing longer than initial lease duration.
        Background heartbeat thread continually renews the lease, preventing
        watchdog from prematurely re-queuing the active task.
        """
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {}, max_attempts=3)

        # Custom handler simulating a long-running scrape
        from app.worker import handlers

        def slow_handler(t: Any, s: Session) -> dict[str, Any]:
            time.sleep(2.5)
            return {"scraped": 42}

        monkeypatch.setitem(handlers.TASK_HANDLERS, "scrape", slow_handler)

        worker = BackgroundWorker(
            worker_id="slow-worker-1",
            lease_seconds=2,  # 2-second lease, handler runs for 2.5s
            session_factory=lambda: cast(Session, _NonClosingSessionWrapper(db)),
        )

        processed = worker.run_once()
        assert processed is True

        db.refresh(task)
        assert task.status == "succeeded"
        assert task.result == {"scraped": 42}

    def test_stale_worker_resuming_after_recovery_cannot_complete_or_fail(
        self,
        db: Session,
    ) -> None:
        """
        Simulate a stale worker whose lease expired and was reclaimed by watchdog.
        When the stale worker resumes, its attempts to complete or fail the task
        must be rejected with TaskLeaseLostError, preserving the re-queued task.
        """
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {}, max_attempts=3)
        claimed = service.claim_task("stale-worker-1", lease_seconds=10)
        assert claimed is not None

        # Expire lease and run watchdog recovery
        task.lease_timeout_at = datetime.now(UTC) - timedelta(seconds=20)
        db.commit()

        recovered = service.recover_stale_tasks(lease_grace_seconds=0)
        assert len(recovered) == 1
        assert recovered[0].status == "queued"
        assert recovered[0].worker_id is None

        # Stale worker attempts to complete task after recovery
        with pytest.raises(TaskLeaseLostError):
            service.complete_task(
                task.id,
                worker_id="stale-worker-1",
                result={"corrupted": True},
                expected_attempt=1,
            )

        # Stale worker attempts to fail task after recovery
        with pytest.raises(TaskLeaseLostError):
            service.fail_task(
                task.id,
                worker_id="stale-worker-1",
                error_message="Stale error",
                expected_attempt=1,
            )

        # Task in DB remains untouched in 'queued' status
        db.refresh(task)
        assert task.status == "queued"
        assert task.worker_id is None

    def test_stale_worker_cannot_overwrite_newer_attempt_by_another_worker(
        self,
        db: Session,
    ) -> None:
        """
        When watchdog recovers a task and a second worker claims attempt 2,
        the first worker's attempt 1 must not be able to heartbeat or complete.
        """
        service = TaskQueueService(db)
        task = service.enqueue("scrape", {}, max_attempts=3)
        w1_task = service.claim_task("worker-1", lease_seconds=10)
        assert w1_task is not None
        assert w1_task.attempt_count == 1

        # Expire and recover
        task.lease_timeout_at = datetime.now(UTC) - timedelta(seconds=10)
        db.commit()
        service.recover_stale_tasks(lease_grace_seconds=0)

        # Reset available_at so worker-2 can claim immediately
        task.available_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

        # Worker 2 claims attempt 2
        w2_task = service.claim_task("worker-2", lease_seconds=60)
        assert w2_task is not None
        assert w2_task.attempt_count == 2
        assert w2_task.worker_id == "worker-2"

        # Worker 1 tries heartbeat with attempt 1
        assert service.heartbeat(task.id, "worker-1", expected_attempt=1) is False

        # Worker 1 tries complete_task with attempt 1
        with pytest.raises(TaskLeaseLostError):
            service.complete_task(task.id, "worker-1", expected_attempt=1)

        # Worker 2 completes attempt 2 successfully
        w2_completed = service.complete_task(
            task.id, "worker-2", result={"worker": 2}, expected_attempt=2
        )
        assert w2_completed.status == "succeeded"


# ── Test Idempotent Enqueueing & Concurrency ────────────────────────────────

class TestIdempotentEnqueueingConcurrency:
    def test_concurrent_enqueue_race_condition_prevented(
        self,
        db_engine: Any,
    ) -> None:
        """
        Simulate concurrent enqueue requests across independent PostgreSQL sessions.
        Ensures that exactly one task is created and all callers receive the same task.
        """
        import threading

        from app.models.user import User

        init_session = Session(db_engine)
        test_user = User(
            id=uuid.uuid4(),
            email=f"concurrent-{uuid.uuid4().hex[:8]}@example.com",
            name="Concurrent Test User",
            password_hash="test-password-hash",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        init_session.add(test_user)
        init_session.commit()
        user_id = test_user.id
        init_session.close()

        concurrency = 6
        barrier = threading.Barrier(concurrency)
        results: list[uuid.UUID] = []
        errors: list[Exception] = []
        key = f"concurrent-test-{uuid.uuid4().hex[:8]}"

        def worker_thread() -> None:
            session = Session(db_engine)
            try:
                barrier.wait(timeout=10.0)
                service = TaskQueueService(session, user_id=user_id)
                task = service.enqueue(
                    task_type="scrape",
                    payload={"run": "concurrent"},
                    idempotency_key=key,
                    user_id=user_id,
                )
                results.append(task.id)
            except Exception as exc:
                errors.append(exc)
            finally:
                session.close()

        threads = [threading.Thread(target=worker_thread) for _ in range(concurrency)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        cleanup_session = Session(db_engine)
        try:
            assert not errors, f"Concurrent enqueue had errors: {errors}"
            assert len(results) == concurrency
            # All callers received the exact same task ID
            assert len(set(results)) == 1

            from app.models.task import Task
            count = (
                cleanup_session.query(Task)
                .filter(Task.idempotency_key == key)
                .count()
            )
            assert count == 1
        finally:
            from app.models.task import Task
            cleanup_session.query(Task).filter(Task.user_id == user_id).delete()
            cleanup_session.query(User).filter(User.id == user_id).delete()
            cleanup_session.commit()
            cleanup_session.close()

    def test_idempotency_scope_isolates_users_and_system(
        self,
        db: Session,
        sample_user: User,
        second_user: User,
    ) -> None:
        """
        Verify that idempotency key uniqueness is correctly scoped by:
        - task_type
        - user ownership (User A != User B != System)
        """
        shared_key = f"scoped-key-{uuid.uuid4().hex[:8]}"

        # User 1 task
        service_u1 = TaskQueueService(db, user_id=sample_user.id)
        task_u1 = service_u1.enqueue(
            "scrape", {"u": 1}, idempotency_key=shared_key, user_id=sample_user.id
        )

        # User 2 task with same key
        service_u2 = TaskQueueService(db, user_id=second_user.id)
        task_u2 = service_u2.enqueue(
            "scrape", {"u": 2}, idempotency_key=shared_key, user_id=second_user.id
        )

        # System task (user_id=None) with same key
        service_sys = TaskQueueService(db)
        task_sys = service_sys.enqueue(
            "scrape", {"sys": True}, idempotency_key=shared_key, user_id=None
        )

        # All 3 tasks must be distinct
        assert task_u1.id != task_u2.id
        assert task_u1.id != task_sys.id
        assert task_u2.id != task_sys.id

        # Re-enqueueing for User 1 returns User 1's existing task
        task_u1_dup = service_u1.enqueue(
            "scrape", {"u": 1}, idempotency_key=shared_key, user_id=sample_user.id
        )
        assert task_u1_dup.id == task_u1.id

        # Re-enqueueing for System returns System's existing task
        task_sys_dup = service_sys.enqueue(
            "scrape", {"sys": True}, idempotency_key=shared_key, user_id=None
        )
        assert task_sys_dup.id == task_sys.id

    def test_idempotency_preserves_valid_retries_after_terminal_state(
        self,
        db: Session,
        sample_user: User,
    ) -> None:
        """
        Once an idempotent task reaches a terminal state (succeeded / failed),
        subsequent enqueue calls with the same key must create a new task.
        """
        service = TaskQueueService(db, user_id=sample_user.id)
        key = f"retry-key-{uuid.uuid4().hex[:8]}"

        # Enqueue initial task
        task1 = service.enqueue("scrape", {}, idempotency_key=key, user_id=sample_user.id)
        claimed = service.claim_task("worker-1")
        assert claimed is not None
        assert claimed.id == task1.id

        # Complete task1 (terminal 'succeeded')
        service.complete_task(task1.id, "worker-1", result={"done": True})
        db.refresh(task1)
        assert task1.status == "succeeded"

        # Enqueue new task with same key
        task2 = service.enqueue("scrape", {}, idempotency_key=key, user_id=sample_user.id)
        assert task2.id != task1.id
        assert task2.status == "queued"


