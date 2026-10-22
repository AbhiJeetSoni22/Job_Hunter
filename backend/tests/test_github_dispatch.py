"""
Unit and integration tests for GitHub Actions repository_dispatch service and enqueue integration (Phase 3).
"""

from __future__ import annotations

import logging
import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import PostgresDsn
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.task import Task
from app.models.user import User
from app.services.github_dispatch_service import (
    GitHubDispatchError,
    GitHubDispatchService,
    mask_token,
    sanitize_error_message,
)
from app.services.rate_limit_service import RateLimitService
from app.services.task_queue_service import TaskQueueService
from tests.conftest import needs_db

# ── Unit Tests: Masking and Secret Sanitization ───────────────────────────────

class TestSanitization:
    def test_mask_token(self) -> None:
        assert mask_token("") == ""
        assert mask_token("short") == "***"
        assert mask_token("12345678") == "***"
        assert mask_token("github_pat_1234567890abcdef") == "***cdef"

    def test_sanitize_error_message_redacts_explicit_token(self) -> None:
        raw_token = "ghp_secretTokenValue1234567890123456"
        msg = f"Failed to authenticate with token {raw_token} on GitHub"
        cleaned = sanitize_error_message(msg, token=raw_token)
        assert raw_token not in cleaned
        assert "***REDACTED_TOKEN***" in cleaned

    def test_sanitize_error_message_redacts_bearer_and_patterns(self) -> None:
        msg = "Request headers: Authorization: Bearer ghp_sample1234567890123456789012345"
        cleaned = sanitize_error_message(msg)
        assert "ghp_sample1234567890123456789012345" not in cleaned
        assert "Bearer ***" in cleaned

    def test_sanitize_error_message_redacts_github_pat(self) -> None:
        msg = "Error using github_pat_11AAAAAAA0000000000000000000000000000"
        cleaned = sanitize_error_message(msg)
        assert "11AAAAAAA0000000000000000000000000000" not in cleaned
        assert "github_pat_***" in cleaned

    def test_sanitize_error_message_redacts_database_urls(self) -> None:
        url = "postgresql://user:super_secret_password@ep-cool-db.us-east-1.aws.neon.tech:5432/neondb"
        msg = f"Database connection error to {url}"
        cleaned = sanitize_error_message(msg)
        assert "super_secret_password" not in cleaned
        assert "postgresql://user:***@ep-cool-db" in cleaned


# ── Unit Tests: GitHubDispatchService ─────────────────────────────────────────

class TestGitHubDispatchService:
    def test_is_configured(self) -> None:
        unconfigured = GitHubDispatchService(token="", owner="", repo="")
        assert unconfigured.is_configured is False

        partial1 = GitHubDispatchService(token="tok", owner="", repo="repo")
        assert partial1.is_configured is False

        partial2 = GitHubDispatchService(token="tok", owner="owner", repo="")
        assert partial2.is_configured is False

        configured = GitHubDispatchService(token="tok", owner="owner", repo="repo")
        assert configured.is_configured is True
        assert configured.dispatch_url == "https://api.github.com/repos/owner/repo/dispatches"

    def test_dispatch_unconfigured_skips_and_returns_false(self, caplog: pytest.LogCaptureFixture) -> None:
        service = GitHubDispatchService(token="", owner="", repo="")
        with caplog.at_level(logging.WARNING):
            result = service.dispatch_task_queue(raise_on_error=False)
        assert result is False
        assert "GitHub Actions dispatch skipped" in caplog.text

    def test_dispatch_unconfigured_raises_when_requested(self) -> None:
        service = GitHubDispatchService(token="", owner="", repo="")
        with pytest.raises(GitHubDispatchError, match="not configured"):
            service.dispatch_task_queue(raise_on_error=True)

    def test_dispatch_success_204(self) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204
        mock_client.post.return_value = mock_response

        service = GitHubDispatchService(
            token="ghp_test_token_12345678901234567890",
            owner="test-owner",
            repo="test-repo",
            httpx_client=mock_client,
        )

        success = service.dispatch_task_queue(
            event_type="process_task_queue",
            client_payload={"task_id": "123"},
        )
        assert success is True

        mock_client.post.assert_called_once()
        call_args, call_kwargs = mock_client.post.call_args
        assert call_args[0] == "https://api.github.com/repos/test-owner/test-repo/dispatches"
        assert call_kwargs["headers"]["Authorization"] == "Bearer ghp_test_token_12345678901234567890"
        assert call_kwargs["headers"]["Accept"] == "application/vnd.github+json"
        assert call_kwargs["headers"]["X-GitHub-Api-Version"] == "2022-11-28"
        assert call_kwargs["json"] == {
            "event_type": "process_task_queue",
            "client_payload": {"task_id": "123"},
        }

    def test_dispatch_http_error_returns_false_and_sanitizes(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        secret_token = "ghp_super_secret_test_token_12345"
        mock_response.text = f"Bad credentials with token {secret_token}"
        mock_client.post.return_value = mock_response

        service = GitHubDispatchService(
            token=secret_token,
            owner="test-owner",
            repo="test-repo",
            httpx_client=mock_client,
        )

        with caplog.at_level(logging.WARNING):
            success = service.dispatch_task_queue(raise_on_error=False)

        assert success is False
        assert secret_token not in caplog.text
        assert "401" in caplog.text

    def test_dispatch_http_error_raises_when_requested(self) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_client.post.return_value = mock_response

        service = GitHubDispatchService(
            token="ghp_test_token_12345678901234567890",
            owner="test-owner",
            repo="test-repo",
            httpx_client=mock_client,
        )

        with pytest.raises(GitHubDispatchError, match="HTTP 403"):
            service.dispatch_task_queue(raise_on_error=True)

    def test_dispatch_timeout_returns_false_and_sanitizes(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        secret_token = "ghp_timeout_token_123456789012345"
        mock_client.post.side_effect = httpx.TimeoutException(f"Timed out on request with {secret_token}")

        service = GitHubDispatchService(
            token=secret_token,
            owner="test-owner",
            repo="test-repo",
            httpx_client=mock_client,
        )

        with caplog.at_level(logging.WARNING):
            success = service.dispatch_task_queue(raise_on_error=False)

        assert success is False
        assert secret_token not in caplog.text
        assert "timed out" in caplog.text.lower()

    def test_dispatch_network_error_returns_false(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused to api.github.com")

        service = GitHubDispatchService(
            token="ghp_test_token_12345678901234567890",
            owner="test-owner",
            repo="test-repo",
            httpx_client=mock_client,
        )

        with caplog.at_level(logging.WARNING):
            success = service.dispatch_task_queue(raise_on_error=False)

        assert success is False
        assert "network error" in caplog.text.lower()


# ── Configuration Startup Tests ──────────────────────────────────────────────

class TestDispatchConfiguration:
    def test_settings_defaults_allow_clean_startup(self) -> None:
        settings = Settings(
            DATABASE_URL=PostgresDsn("postgresql://user:pass@localhost:5432/testdb"),
            GEMINI_API_KEY="test-gemini-key",
            JWT_SECRET_KEY="test-secret-key-at-least-32-characters-long",
        )
        assert settings.GITHUB_DISPATCH_TOKEN == ""
        assert settings.GITHUB_REPO_OWNER == ""
        assert settings.GITHUB_REPO_NAME == ""
        assert settings.is_github_dispatch_configured is False

    def test_settings_strips_whitespace(self) -> None:
        settings = Settings(
            DATABASE_URL=PostgresDsn("postgresql://user:pass@localhost:5432/testdb"),
            GEMINI_API_KEY="test-gemini-key",
            JWT_SECRET_KEY="test-secret-key-at-least-32-characters-long",
            GITHUB_DISPATCH_TOKEN="  token123  ",
            GITHUB_REPO_OWNER="  my-org  ",
            GITHUB_REPO_NAME="  my-repo  ",
        )
        assert settings.GITHUB_DISPATCH_TOKEN == "token123"
        assert settings.GITHUB_REPO_OWNER == "my-org"
        assert settings.GITHUB_REPO_NAME == "my-repo"
        assert settings.is_github_dispatch_configured is True


# ── Integration Tests: Enqueue Endpoint & Dispatch Behavior ──────────────────

@needs_db
class TestEnqueueEndpointDispatchIntegration:
    def test_enqueue_persists_task_and_triggers_dispatch(
        self,
        db: Session,
        sample_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        """Task is committed to PostgreSQL before dispatch and dispatch is invoked."""
        with patch("app.routers.scraper.GitHubDispatchService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.is_configured = True
            mock_service.dispatch_task_queue.return_value = True
            mock_service_cls.return_value = mock_service

            resp = client.post("/api/scraper/enqueue", headers=auth_headers)
            assert resp.status_code == 202
            data = resp.json()["data"]
            task_id = uuid.UUID(data["id"])

            # Verify persisted in DB
            db_task = db.query(Task).filter(Task.id == task_id).first()
            assert db_task is not None
            assert db_task.status == "queued"
            assert db_task.task_type == "scrape"

            # Verify dispatch service was called with process_task_queue
            mock_service.dispatch_task_queue.assert_called_once_with(
                event_type="process_task_queue",
                client_payload={"task_id": str(task_id)},
                raise_on_error=False,
            )

    def test_enqueue_succeeds_even_when_dispatch_fails(
        self,
        db: Session,
        sample_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        """When dispatch returns False, task is still 202 Accepted and queued in DB."""
        with patch("app.routers.scraper.GitHubDispatchService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.is_configured = True
            mock_service.dispatch_task_queue.return_value = False
            mock_service_cls.return_value = mock_service

            resp = client.post("/api/scraper/enqueue", headers=auth_headers)
            assert resp.status_code == 202
            data = resp.json()["data"]
            task_id = uuid.UUID(data["id"])

            # Task remains successfully queued in database
            db_task = db.query(Task).filter(Task.id == task_id).first()
            assert db_task is not None
            assert db_task.status == "queued"

    def test_enqueue_succeeds_even_when_dispatch_raises_exception(
        self,
        db: Session,
        sample_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        """Even an unexpected exception during dispatch does not fail the HTTP request or rollback task."""
        with patch("app.routers.scraper.GitHubDispatchService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.is_configured = True
            mock_service.dispatch_task_queue.side_effect = RuntimeError("Network timeout")
            mock_service_cls.return_value = mock_service

            resp = client.post("/api/scraper/enqueue", headers=auth_headers)
            assert resp.status_code == 202
            data = resp.json()["data"]
            task_id = uuid.UUID(data["id"])

            db_task = db.query(Task).filter(Task.id == task_id).first()
            assert db_task is not None
            assert db_task.status == "queued"

    def test_enqueue_skips_duplicate_dispatch_on_idempotent_call(
        self,
        db: Session,
        sample_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
    ) -> None:
        with (
            patch("app.routers.scraper.GitHubDispatchService") as mock_service_cls,
            patch.object(RateLimitService, "scraper_run_guard") as mock_guard,
        ):
            mock_guard.return_value.__enter__.return_value = None
            mock_guard.return_value.__exit__.return_value = None

            mock_service = MagicMock()
            mock_service.is_configured = True
            mock_service.dispatch_task_queue.return_value = True
            mock_service_cls.return_value = mock_service

            # First enqueue
            resp1 = client.post("/api/scraper/enqueue", headers=auth_headers)
            assert resp1.status_code == 202
            task_id_1 = resp1.json()["data"]["id"]
            assert mock_service.dispatch_task_queue.call_count == 1

            # Second enqueue while first is still active (queued)
            resp2 = client.post("/api/scraper/enqueue", headers=auth_headers)
            assert resp2.status_code == 202
            task_id_2 = resp2.json()["data"]["id"]

            # Idempotent return of the same task
            assert task_id_1 == task_id_2
            # Crucial: dispatch count remains 1, no duplicate dispatch was triggered!
            assert mock_service.dispatch_task_queue.call_count == 1

    def test_enqueue_when_dispatch_not_configured_logs_warning_and_succeeds(
        self,
        db: Session,
        sample_user: User,
        auth_headers: dict[str, str],
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When GitHub dispatch is unconfigured, task is queued and HTTP 202 returned without errors."""
        with patch("app.routers.scraper.GitHubDispatchService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.is_configured = False
            mock_service_cls.return_value = mock_service

            with caplog.at_level(logging.WARNING):
                resp = client.post("/api/scraper/enqueue", headers=auth_headers)

            assert resp.status_code == 202
            assert mock_service.dispatch_task_queue.call_count == 0
            assert "GitHub Actions dispatch skipped" in caplog.text

    def test_task_queue_service_is_new_tagging(
        self,
        db: Session,
        sample_user: User,
    ) -> None:
        """TaskQueueService marks newly enqueued tasks with _is_new=True and deduplicated tasks with _is_new=False."""
        service = TaskQueueService(db, user_id=sample_user.id)
        idemp_key = f"unique-test-key-{uuid.uuid4()}"

        task1 = service.enqueue("scrape", {"k": 1}, idempotency_key=idemp_key)
        assert getattr(task1, "_is_new", False) is True

        task2 = service.enqueue("scrape", {"k": 1}, idempotency_key=idemp_key)
        assert task2.id == task1.id
        assert getattr(task2, "_is_new", True) is False
