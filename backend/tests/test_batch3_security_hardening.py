"""
test_batch3_security_hardening.py

Comprehensive tests for Phase 0 — Batch 3 Security Hardening:
1. Bounded resume upload & PDF magic-byte validation
2. AI per-user rate limiting (AI_RATE_LIMIT_PER_MINUTE)
3. Scraper cooldown (SCRAPER_COOLDOWN_SECONDS) & concurrency locking
4. Configurable bulk score limit (MAX_BULK_SCORE_LIMIT)
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import create_access_token
from app.models.job import Job
from app.models.rate_limit import RateLimitEvent
from app.models.resume import Resume
from app.models.user import User
from app.schemas.job import ScraperRunSummary, ScrapeRunResponse
from tests.conftest import needs_db

pytestmark = needs_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def user_one(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"user1-{uuid.uuid4().hex[:6]}@example.com",
        name="User One",
        password_hash="hash-user-1",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def user_two(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"user2-{uuid.uuid4().hex[:6]}@example.com",
        name="User Two",
        password_hash="hash-user-2",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def auth_headers_one(user_one: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user_one.id), "email": user_one.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers_two(user_two: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user_two.id), "email": user_two.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def resume_one(db: Session, user_one: User) -> Resume:
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user_one.id,
        filename="user1_resume.pdf",
        raw_text="Python FastAPI Docker Kubernetes PostgreSQL AWS",
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        uploaded_at=datetime.now(UTC),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@pytest.fixture()
def resume_two(db: Session, user_two: User) -> Resume:
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user_two.id,
        filename="user2_resume.pdf",
        raw_text="Go Kubernetes AWS Terraform",
        skills=["Go", "Kubernetes", "AWS"],
        uploaded_at=datetime.now(UTC),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@pytest.fixture()
def test_job(db: Session) -> Job:
    job = Job(
        id=uuid.uuid4(),
        title="Senior Python Backend Developer",
        company="Tech Corp",
        description="FastAPI, PostgreSQL, Docker, and distributed systems experience required.",
        url=f"https://example.com/jobs/{uuid.uuid4().hex[:8]}",
        source="remoteok",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture(autouse=True)
def mock_all_gemini() -> Generator[MagicMock, None, None]:
    with (
        patch("app.services.match_service.GeminiClient") as MockMatch,
        patch("app.services.resume_service.GeminiClient") as MockResume,
        patch("app.services.resume_analysis_service.GeminiClient") as MockAnalysis,
        patch("app.services.interview_prep_service.GeminiClient") as MockPrep,
    ):
        mock_instance = MagicMock()
        mock_instance.match_job.return_value = {
            "match_score": 80,
            "missing_skills": ["Docker"],
            "match_summary": "Good fit.",
        }
        mock_instance.extract_skills.return_value = ["Python", "FastAPI"]
        mock_instance.analyze_resume_gap.return_value = {
            "match_score": 85,
            "match_summary": "Strong alignment.",
            "missing_skills": [],
            "existing_strengths": ["Python"],
            "resume_improvements": [],
            "ats_tips": [],
        }
        mock_instance.generate_interview_prep.return_value = {
            "technical_questions": ["What is FastAPI dependency injection?"],
            "behavioral_questions": ["Tell me about a time you handled a bug."],
            "resume_questions": ["Explain your Docker project."],
            "topics_to_revise": ["FastAPI"],
            "interview_tips": ["Be concise."],
        }
        MockMatch.return_value = mock_instance
        MockResume.return_value = mock_instance
        MockAnalysis.return_value = mock_instance
        MockPrep.return_value = mock_instance
        yield mock_instance


# ---------------------------------------------------------------------------
# 1. AI Rate Limiting Tests
# ---------------------------------------------------------------------------


class TestAIRateLimiting:
    def test_requests_under_limit_succeed(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        resume_one: Resume,
        test_job: Job,
        mock_gemini: MagicMock,
    ) -> None:
        """Requests under AI_RATE_LIMIT_PER_MINUTE succeed."""
        settings = get_settings()
        assert settings.AI_RATE_LIMIT_PER_MINUTE > 0

        # Run 2 requests — well below limit of 30
        for _ in range(2):
            res = client.post(
                f"/api/jobs/{test_job.id}/score",
                headers=auth_headers_one,
            )
            assert res.status_code == 200

    def test_request_exceeding_limit_returns_429(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        user_one: User,
        resume_one: Resume,
        test_job: Job,
        db: Session,
        mock_gemini: MagicMock,
    ) -> None:
        """When AI rate limit is reached, subsequent request returns HTTP 429."""
        settings = get_settings()
        limit = settings.AI_RATE_LIMIT_PER_MINUTE
        now = datetime.now(UTC)

        # Pre-seed the database with (limit) rate limit events within the last 60 seconds
        for _ in range(limit):
            event = RateLimitEvent(
                id=uuid.uuid4(),
                user_id=user_one.id,
                event_type="ai_operation",
                status="completed",
                created_at=now - timedelta(seconds=10),
                completed_at=now - timedelta(seconds=10),
            )
            db.add(event)
        db.commit()

        # The next request must be rejected with 429
        res = client.post(
            f"/api/jobs/{test_job.id}/score",
            headers=auth_headers_one,
        )
        assert res.status_code == 429
        data = res.json()
        assert data["data"] is None
        assert data["error"]["code"] == "AI_RATE_LIMIT_EXCEEDED"
        assert "rate limit" in data["error"]["message"].lower()

    def test_rate_limit_is_scoped_per_user(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        auth_headers_two: dict[str, str],
        user_one: User,
        user_two: User,
        resume_one: Resume,
        resume_two: Resume,
        test_job: Job,
        db: Session,
        mock_gemini: MagicMock,
    ) -> None:
        """User A exhausting their quota does not block User B."""
        settings = get_settings()
        limit = settings.AI_RATE_LIMIT_PER_MINUTE
        now = datetime.now(UTC)

        # Pre-seed User One to reach limit
        for _ in range(limit):
            db.add(
                RateLimitEvent(
                    id=uuid.uuid4(),
                    user_id=user_one.id,
                    event_type="ai_operation",
                    status="completed",
                    created_at=now - timedelta(seconds=5),
                    completed_at=now - timedelta(seconds=5),
                )
            )
        db.commit()

        # User One is rate limited
        res1 = client.post(f"/api/jobs/{test_job.id}/score", headers=auth_headers_one)
        assert res1.status_code == 429
        assert res1.json()["error"]["code"] == "AI_RATE_LIMIT_EXCEEDED"

        # User Two has unused quota and succeeds
        res2 = client.post(f"/api/jobs/{test_job.id}/score", headers=auth_headers_two)
        assert res2.status_code == 200

    def test_requests_after_window_elapses_succeed(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        user_one: User,
        resume_one: Resume,
        test_job: Job,
        db: Session,
        mock_gemini: MagicMock,
    ) -> None:
        """Old events (>60s) do not count towards the current 1-minute rate limit."""
        settings = get_settings()
        limit = settings.AI_RATE_LIMIT_PER_MINUTE
        old_time = datetime.now(UTC) - timedelta(seconds=65)

        # Seed events from >60s ago
        for _ in range(limit):
            db.add(
                RateLimitEvent(
                    id=uuid.uuid4(),
                    user_id=user_one.id,
                    event_type="ai_operation",
                    status="completed",
                    created_at=old_time,
                    completed_at=old_time,
                )
            )
        db.commit()

        # Request succeeds because the window has rolled past the old events
        res = client.post(f"/api/jobs/{test_job.id}/score", headers=auth_headers_one)
        assert res.status_code == 200

    def test_bulk_score_counts_as_one_ai_event(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        user_one: User,
        resume_one: Resume,
        test_job: Job,
        db: Session,
    ) -> None:
        """Bulk scoring request counts as 1 rate-limit operation regardless of job count."""
        with patch("app.routers.scraper._auto_score_in_background"):
            res = client.post("/api/jobs/bulk-score", headers=auth_headers_one)
            assert res.status_code == 200

        # Verify exactly 1 rate limit event was inserted for this user
        events = (
            db.query(RateLimitEvent)
            .filter(
                RateLimitEvent.user_id == user_one.id,
                RateLimitEvent.event_type == "ai_operation",
            )
            .all()
        )
        assert len(events) == 1

    def test_resume_analyze_is_rate_limited(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        user_one: User,
        resume_one: Resume,
        db: Session,
        mock_gemini: MagicMock,
    ) -> None:
        """POST /api/resume/analyze is covered by AI rate limiting."""
        settings = get_settings()
        now = datetime.now(UTC)

        for _ in range(settings.AI_RATE_LIMIT_PER_MINUTE):
            db.add(
                RateLimitEvent(
                    id=uuid.uuid4(),
                    user_id=user_one.id,
                    event_type="ai_operation",
                    status="completed",
                    created_at=now,
                    completed_at=now,
                )
            )
        db.commit()

        res = client.post(
            "/api/resume/analyze",
            headers=auth_headers_one,
            json={
                "job_description": "We need a Senior Python and FastAPI Engineer with Docker experience."
            },
        )
        assert res.status_code == 429
        assert res.json()["error"]["code"] == "AI_RATE_LIMIT_EXCEEDED"

    def test_interview_prep_is_rate_limited(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        user_one: User,
        resume_one: Resume,
        test_job: Job,
        db: Session,
        mock_gemini: MagicMock,
    ) -> None:
        """POST /api/jobs/{job_id}/interview-prep is covered by AI rate limiting."""
        settings = get_settings()
        now = datetime.now(UTC)

        for _ in range(settings.AI_RATE_LIMIT_PER_MINUTE):
            db.add(
                RateLimitEvent(
                    id=uuid.uuid4(),
                    user_id=user_one.id,
                    event_type="ai_operation",
                    status="completed",
                    created_at=now,
                    completed_at=now,
                )
            )
        db.commit()

        res = client.post(
            f"/api/jobs/{test_job.id}/interview-prep",
            headers=auth_headers_one,
        )
        assert res.status_code == 429
        assert res.json()["error"]["code"] == "AI_RATE_LIMIT_EXCEEDED"

    def test_get_endpoints_are_not_rate_limited(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        user_one: User,
        resume_one: Resume,
        test_job: Job,
        db: Session,
    ) -> None:
        """Normal GET endpoints are never affected by AI rate limiting."""
        settings = get_settings()
        now = datetime.now(UTC)

        for _ in range(settings.AI_RATE_LIMIT_PER_MINUTE + 5):
            db.add(
                RateLimitEvent(
                    id=uuid.uuid4(),
                    user_id=user_one.id,
                    event_type="ai_operation",
                    status="completed",
                    created_at=now,
                    completed_at=now,
                )
            )
        db.commit()

        # Normal GET /api/jobs
        res_jobs = client.get("/api/jobs", headers=auth_headers_one)
        assert res_jobs.status_code == 200

        # Normal GET /api/jobs/{id}
        res_job = client.get(f"/api/jobs/{test_job.id}", headers=auth_headers_one)
        assert res_job.status_code == 200

        # Normal GET /api/resume
        res_resume = client.get("/api/resume", headers=auth_headers_one)
        assert res_resume.status_code == 200


# ---------------------------------------------------------------------------
# 2. Scraper Cooldown & Concurrency Protection Tests
# ---------------------------------------------------------------------------


class TestScraperCooldownAndConcurrency:
    def _mock_summary(self) -> ScraperRunSummary:
        return ScraperRunSummary(
            runs=[
                ScrapeRunResponse(
                    source="remoteok",
                    jobs_found=2,
                    jobs_new=1,
                    error=None,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                ),
            ],
            total_new=1,
            total_scored=0,
            new_job_ids=[],
        )

    def test_first_scraper_request_succeeds(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
    ) -> None:
        """First scraper request succeeds and returns summary."""
        with patch(
            "app.services.scraper_service.ScraperService.run_all",
            return_value=(self._mock_summary(), []),
        ):
            res = client.post("/api/scraper/run", headers=auth_headers_one)
            assert res.status_code == 200
            assert res.json()["data"]["total_new"] == 1

    def test_second_scraper_request_during_cooldown_returns_429(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        user_one: User,
        db: Session,
    ) -> None:
        """Second scraper request within SCRAPER_COOLDOWN_SECONDS returns 429."""
        now = datetime.now(UTC)

        # Seed a completed scraper run 10 seconds ago
        db.add(
            RateLimitEvent(
                id=uuid.uuid4(),
                user_id=user_one.id,
                event_type="scraper_run",
                status="completed",
                created_at=now - timedelta(seconds=10),
                completed_at=now - timedelta(seconds=10),
            )
        )
        db.commit()

        res = client.post("/api/scraper/run", headers=auth_headers_one)
        assert res.status_code == 429
        data = res.json()
        assert data["data"] is None
        assert data["error"]["code"] == "SCRAPER_RATE_LIMITED"
        assert "cooldown" in data["error"]["message"].lower()

    def test_scraper_request_after_cooldown_succeeds(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        user_one: User,
        db: Session,
    ) -> None:
        """After cooldown period elapses, next scraper request succeeds."""
        settings = get_settings()
        cooldown = settings.SCRAPER_COOLDOWN_SECONDS
        old_time = datetime.now(UTC) - timedelta(seconds=cooldown + 5)

        # Seed completed run past the cooldown window
        db.add(
            RateLimitEvent(
                id=uuid.uuid4(),
                user_id=user_one.id,
                event_type="scraper_run",
                status="completed",
                created_at=old_time,
                completed_at=old_time,
            )
        )
        db.commit()

        with patch(
            "app.services.scraper_service.ScraperService.run_all",
            return_value=(self._mock_summary(), []),
        ):
            res = client.post("/api/scraper/run", headers=auth_headers_one)
            assert res.status_code == 200

    def test_concurrent_duplicate_scraper_rejected(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        user_one: User,
        db: Session,
    ) -> None:
        """Active in-progress scraper run rejects concurrent trigger for same user."""
        now = datetime.now(UTC)

        # Seed an in_progress scraper run for user one
        db.add(
            RateLimitEvent(
                id=uuid.uuid4(),
                user_id=user_one.id,
                event_type="scraper_run",
                status="in_progress",
                created_at=now - timedelta(seconds=5),
            )
        )
        db.commit()

        res = client.post("/api/scraper/run", headers=auth_headers_one)
        assert res.status_code == 429
        data = res.json()
        assert data["error"]["code"] == "SCRAPER_RATE_LIMITED"
        assert "already in progress" in data["error"]["message"].lower()

    def test_scraper_cooldown_is_user_scoped(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        auth_headers_two: dict[str, str],
        user_one: User,
        user_two: User,
        db: Session,
    ) -> None:
        """User A in cooldown does not prevent User B from scraping."""
        now = datetime.now(UTC)

        # User One is in cooldown
        db.add(
            RateLimitEvent(
                id=uuid.uuid4(),
                user_id=user_one.id,
                event_type="scraper_run",
                status="completed",
                created_at=now - timedelta(seconds=5),
                completed_at=now - timedelta(seconds=5),
            )
        )
        db.commit()

        # User One returns 429
        res1 = client.post("/api/scraper/run", headers=auth_headers_one)
        assert res1.status_code == 429
        assert res1.json()["error"]["code"] == "SCRAPER_RATE_LIMITED"

        # User Two has no cooldown and succeeds
        with patch(
            "app.services.scraper_service.ScraperService.run_all",
            return_value=(self._mock_summary(), []),
        ):
            res2 = client.post("/api/scraper/run", headers=auth_headers_two)
            assert res2.status_code == 200


# ---------------------------------------------------------------------------
# 3. Bulk Score Limit from Configuration Tests
# ---------------------------------------------------------------------------


class TestBulkScoreConfiguration:
    def test_bulk_score_respects_max_limit_from_settings(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        resume_one: Resume,
    ) -> None:
        """POST /api/jobs/bulk-score rejects requests exceeding settings.MAX_BULK_SCORE_LIMIT."""
        settings = get_settings()
        oversized = settings.MAX_BULK_SCORE_LIMIT + 1

        res = client.post(
            f"/api/jobs/bulk-score?limit={oversized}",
            headers=auth_headers_one,
        )
        assert res.status_code == 422
        data = res.json()
        assert data["data"] is None
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert (
            f"limit cannot exceed {settings.MAX_BULK_SCORE_LIMIT}"
            in data["error"]["message"]
        )

    def test_bulk_score_allows_request_at_configured_limit(
        self,
        client: TestClient,
        auth_headers_one: dict[str, str],
        resume_one: Resume,
    ) -> None:
        """POST /api/jobs/bulk-score allows requests up to settings.MAX_BULK_SCORE_LIMIT."""
        settings = get_settings()
        at_limit = settings.MAX_BULK_SCORE_LIMIT

        with patch("app.routers.scraper._auto_score_in_background"):
            res = client.post(
                f"/api/jobs/bulk-score?limit={at_limit}",
                headers=auth_headers_one,
            )
            assert res.status_code == 200
