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

