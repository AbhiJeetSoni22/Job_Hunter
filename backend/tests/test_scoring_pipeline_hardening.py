"""
test_scoring_pipeline_hardening.py

Comprehensive tests for Phase 0 Batch 1: Scoring Pipeline Correctness.

Verifies:
1. Normal scoring (cache miss)
2. Force rescore (bypasses cache for fresh and stale jobs)
3. Stale score refresh
4. Unscored job scoring
5. Bulk scoring of unscored and stale jobs
6. Zero eligible jobs safety
7. Malformed Gemini response handling (does not abort batch)
8. Gemini API failure handling
9. Scoring exception handling
10. ScoringRun becomes 'failed' instead of remaining 'running' on run crash
11. Previous valid score survives failed rescore
12. Stuck scoring run recovery (timeout-based reconciliation)
13. User data isolation (User A cannot affect User B's scores/runs)
14. Concurrent scoring protection (HTTP 409 if a run is already active)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gemini_client import AIError
from app.core.security import create_access_token
from app.models.job import Job
from app.models.resume import Resume
from app.models.scoring_run import ScoringRun
from app.models.user import User
from app.models.user_job import UserJob
from app.services.job_service import JobService
from app.services.match_service import score_job
from app.services.scraper_service import ScraperService
from tests.conftest import needs_db

pytestmark = needs_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def user_alpha(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"alpha-{uuid.uuid4().hex[:6]}@example.com",
        name="User Alpha",
        password_hash="hash-alpha",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def user_beta(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"beta-{uuid.uuid4().hex[:6]}@example.com",
        name="User Beta",
        password_hash="hash-beta",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def resume_alpha(db: Session, user_alpha: User) -> Resume:
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user_alpha.id,
        filename="alpha_resume.pdf",
        raw_text="Python FastAPI Docker PostgreSQL",
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        uploaded_at=datetime.now(UTC),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@pytest.fixture()
def resume_beta(db: Session, user_beta: User) -> Resume:
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user_beta.id,
        filename="beta_resume.pdf",
        raw_text="Go Kubernetes AWS",
        skills=["Go", "Kubernetes", "AWS"],
        uploaded_at=datetime.now(UTC),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@pytest.fixture()
def sample_jobs(db: Session) -> list[Job]:
    jobs = []
    for i in range(3):
        job = Job(
            id=uuid.uuid4(),
            title=f"Engineer {i}",
            company="Acme Corp",
            description=f"Job description {i} requiring Python and Docker",
            url=f"https://example.com/job-{uuid.uuid4().hex}",
            source="remoteok",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(job)
        jobs.append(job)
    db.commit()
    for j in jobs:
        db.refresh(j)
    return jobs


@pytest.fixture()
def auth_headers_alpha(user_alpha: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user_alpha.id), "email": user_alpha.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers_beta(user_beta: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user_beta.id), "email": user_beta.email})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests: Force Rescore & Score Caching
# ---------------------------------------------------------------------------

class TestForceRescorePipeline:

    def test_force_rescore_via_endpoint(self, client, auth_headers_alpha, sample_jobs, resume_alpha, db):
        job = sample_jobs[0]

        with patch("app.services.match_service.GeminiClient") as MockGemini:
            MockGemini.return_value.match_job.return_value = {
                "match_score": 75,
                "missing_skills": ["Kubernetes"],
                "match_summary": "Initial match.",
            }
            res1 = client.post(f"/api/jobs/{job.id}/score", headers=auth_headers_alpha)
            assert res1.status_code == 200
            data1 = res1.json()["data"]
            assert data1["match_score"] == 75
            assert data1["cached"] is False

        # Calling without force should hit cache
        with patch("app.services.match_service.GeminiClient") as MockGemini:
            res2 = client.post(f"/api/jobs/{job.id}/score", headers=auth_headers_alpha)
            assert res2.status_code == 200
            data2 = res2.json()["data"]
            assert data2["match_score"] == 75
            assert data2["cached"] is True
            assert not MockGemini.return_value.match_job.called

        # Calling with force=true must bypass cache and call Gemini
        with patch("app.services.match_service.GeminiClient") as MockGemini:
            MockGemini.return_value.match_job.return_value = {
                "match_score": 90,
                "missing_skills": [],
                "match_summary": "Updated match score.",
            }
            res3 = client.post(f"/api/jobs/{job.id}/score?force=true", headers=auth_headers_alpha)
            assert res3.status_code == 200
            data3 = res3.json()["data"]
            assert data3["match_score"] == 90
            assert data3["cached"] is False
            MockGemini.return_value.match_job.assert_called_once()

    def test_failed_rescore_preserves_valid_score(self, client, auth_headers_alpha, sample_jobs, resume_alpha, db):
        job = sample_jobs[0]

        # Initial successful score
        with patch("app.services.match_service.GeminiClient") as MockGemini:
            MockGemini.return_value.match_job.return_value = {
                "match_score": 85,
                "missing_skills": [],
                "match_summary": "Good fit.",
            }
            res = client.post(f"/api/jobs/{job.id}/score", headers=auth_headers_alpha)
            assert res.status_code == 200

        # Rescore fails with AIError
        with patch("app.services.match_service.GeminiClient") as MockGemini:
            MockGemini.return_value.match_job.side_effect = AIError("Gemini rate limit exceeded")
            res_fail = client.post(f"/api/jobs/{job.id}/score?force=true", headers=auth_headers_alpha)
            assert res_fail.status_code == 502
            err = res_fail.json()["error"]
            assert err["code"] == "AI_ERROR"

        # Verify previous score is still in DB
        uj = db.scalar(select(UserJob).where(UserJob.job_id == job.id, UserJob.user_id == resume_alpha.user_id))
        assert uj is not None
        assert uj.match_score == 85


# ---------------------------------------------------------------------------
# Tests: Bulk Scoring
# ---------------------------------------------------------------------------

class TestBulkScoring:

    def test_find_unscored_and_stale_jobs(self, db, user_alpha, resume_alpha, sample_jobs):
        job_service = JobService(db, user_id=user_alpha.id)

        # Initially all 3 jobs are unscored
        unscored = job_service.find_unscored_and_stale_job_ids(user_id=user_alpha.id)
        assert len(unscored) == 3

        # Score job 0 with current resume
        uj0 = UserJob(
            id=uuid.uuid4(),
            user_id=user_alpha.id,
            job_id=sample_jobs[0].id,
            match_score=80,
            resume_uploaded_at=resume_alpha.uploaded_at,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(uj0)

        # Score job 1 with older resume timestamp (stale)
        uj1 = UserJob(
            id=uuid.uuid4(),
            user_id=user_alpha.id,
            job_id=sample_jobs[1].id,
            match_score=70,
            resume_uploaded_at=datetime.now(UTC) - timedelta(days=5),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(uj1)
        db.commit()

        # With include_stale=True: job 1 (stale) and job 2 (unscored) are eligible
        eligible_with_stale = job_service.find_unscored_and_stale_job_ids(
            user_id=user_alpha.id, include_stale=True
        )
        assert set(eligible_with_stale) == {sample_jobs[1].id, sample_jobs[2].id}

        # With include_stale=False: only job 2 (unscored) is eligible
        unscored_only = job_service.find_unscored_and_stale_job_ids(
            user_id=user_alpha.id, include_stale=False
        )
        assert set(unscored_only) == {sample_jobs[2].id}

    def test_bulk_score_zero_eligible_jobs(self, client, auth_headers_alpha, db, user_alpha, resume_alpha, sample_jobs):
        # Mark all sample jobs as scored with current resume
        for j in sample_jobs:
            uj = UserJob(
                id=uuid.uuid4(),
                user_id=user_alpha.id,
                job_id=j.id,
                match_score=85,
                resume_uploaded_at=resume_alpha.uploaded_at,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(uj)
        db.commit()

        res = client.post("/api/jobs/bulk-score", headers=auth_headers_alpha)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total_eligible"] == 0
        assert data["scoring_run_id"] is None
        assert data["status"] == "completed"

    def test_bulk_score_starts_background_run(self, client, auth_headers_alpha, sample_jobs, resume_alpha, db):
        with patch("app.routers.scraper._auto_score_in_background"):
            res = client.post("/api/jobs/bulk-score", headers=auth_headers_alpha)
            assert res.status_code == 200
            data = res.json()["data"]
            assert data["total_eligible"] == len(sample_jobs)
            assert data["scoring_run_id"] is not None
            assert data["status"] == "running"

            # Check that ScoringRun was created in DB
            run = db.get(ScoringRun, uuid.UUID(data["scoring_run_id"]))
            assert run is not None
            assert run.user_id == resume_alpha.user_id
            assert run.status == "running"

    def test_concurrent_bulk_scoring_protection(self, client, auth_headers_alpha, sample_jobs, resume_alpha, db):
        # Create an actively running scoring run
        service = ScraperService(db, user_id=resume_alpha.user_id)
        active_run = service.start_scoring_run(total_jobs=3, user_id=resume_alpha.user_id)

        res = client.post("/api/jobs/bulk-score", headers=auth_headers_alpha)
        assert res.status_code == 409
        err = res.json()["error"]
        assert err["code"] == "SCORING_IN_PROGRESS"
        assert "already in progress" in err["message"]


# ---------------------------------------------------------------------------
# Tests: Gemini Failures & Malformed Output
# ---------------------------------------------------------------------------

class TestGeminiFailureHardening:

    def test_malformed_response_does_not_abort_batch(self, db, user_alpha, resume_alpha, sample_jobs):
        service = ScraperService(db, user_id=user_alpha.id)
        run = service.start_scoring_run(total_jobs=2, user_id=user_alpha.id)

        job_ids = [str(sample_jobs[0].id), str(sample_jobs[1].id)]

        with patch("app.services.match_service.GeminiClient") as MockGemini:
            # First job raises ValueError (malformed JSON/missing fields); second succeeds
            MockGemini.return_value.match_job.side_effect = [
                ValueError("Response missing 'match_score'"),
                {"match_score": 82, "missing_skills": [], "match_summary": "Good fit."},
            ]
            service.run_auto_score(job_ids, scoring_run_id=run.id, user_id=user_alpha.id, force=True)

        finished = service.get_scoring_run(run.id, user_id=user_alpha.id)
        assert finished.status == "completed"
        assert finished.scored_jobs == 1
        assert finished.failed_jobs == 1
        assert finished.total_jobs == 2

    def test_unhandled_crash_marks_scoring_run_failed(self, db, user_alpha, resume_alpha, sample_jobs):
        service = ScraperService(db, user_id=user_alpha.id)
        run = service.start_scoring_run(total_jobs=2, user_id=user_alpha.id)

        job_ids = [str(sample_jobs[0].id), str(sample_jobs[1].id)]

        with patch.object(service, "_auto_score_new_jobs", side_effect=RuntimeError("Worker crashed unexpectedly")):
            service.run_auto_score(job_ids, scoring_run_id=run.id, user_id=user_alpha.id)

        finished = service.get_scoring_run(run.id, user_id=user_alpha.id)
        assert finished.status == "failed"
        assert finished.completed_at is not None
        assert finished.error_message is not None
        assert "Worker crashed" in finished.error_message


# ---------------------------------------------------------------------------
# Tests: Stuck Scoring Run Recovery
# ---------------------------------------------------------------------------

class TestStuckRunRecovery:

    def test_reconcile_stuck_runs_after_timeout(self, db, user_alpha):
        service = ScraperService(db, user_id=user_alpha.id)

        # Create a run that started 30 minutes ago and was left running
        stuck_run = ScoringRun(
            id=uuid.uuid4(),
            user_id=user_alpha.id,
            status="running",
            total_jobs=5,
            scored_jobs=2,
            failed_jobs=0,
            created_at=datetime.now(UTC) - timedelta(minutes=30),
        )
        db.add(stuck_run)
        db.commit()

        # Reconcile runs older than 15 minutes
        reconciled = service.reconcile_stuck_runs(timeout_minutes=15, user_id=user_alpha.id)
        assert len(reconciled) == 1
        assert reconciled[0].id == stuck_run.id
        assert reconciled[0].status == "failed"
        assert reconciled[0].failed_jobs == 3  # 5 - 2
        assert reconciled[0].completed_at is not None
        assert "timed out" in (reconciled[0].error_message or "")

    def test_reconcile_leaves_active_runs_untouched(self, db, user_alpha):
        service = ScraperService(db, user_id=user_alpha.id)

        # Create a run that started 1 minute ago
        active_run = ScoringRun(
            id=uuid.uuid4(),
            user_id=user_alpha.id,
            status="running",
            total_jobs=5,
            scored_jobs=1,
            failed_jobs=0,
            created_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(active_run)
        db.commit()

        reconciled = service.reconcile_stuck_runs(timeout_minutes=15, user_id=user_alpha.id)
        assert len(reconciled) == 0

        current = service.get_scoring_run(active_run.id, user_id=user_alpha.id)
        assert current.status == "running"

    def test_recover_stuck_runs_endpoint(self, client, auth_headers_alpha, db, user_alpha):
        stuck_run = ScoringRun(
            id=uuid.uuid4(),
            user_id=user_alpha.id,
            status="running",
            total_jobs=3,
            created_at=datetime.now(UTC) - timedelta(minutes=25),
        )
        db.add(stuck_run)
        db.commit()

        res = client.post("/api/scraper/recover-stuck-runs", headers=auth_headers_alpha)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["reconciled_count"] == 1
        assert str(stuck_run.id) in data["reconciled_ids"]


# ---------------------------------------------------------------------------
# Tests: Multi-User Isolation in Scoring
# ---------------------------------------------------------------------------

class TestScoringIsolation:

    def test_user_a_cannot_view_or_poll_user_b_scoring_run(
        self, client, auth_headers_alpha, auth_headers_beta, db, user_beta
    ):
        service = ScraperService(db, user_id=user_beta.id)
        run_b = service.start_scoring_run(total_jobs=1, user_id=user_beta.id)

        # User Beta can access their own run
        res_beta = client.get(f"/api/scraper/scoring-status?run_id={run_b.id}", headers=auth_headers_beta)
        assert res_beta.status_code == 200

        # User Alpha must receive 404
        res_alpha = client.get(f"/api/scraper/scoring-status?run_id={run_b.id}", headers=auth_headers_alpha)
        assert res_alpha.status_code == 404

    def test_user_a_scoring_does_not_affect_user_b_score(
        self, client, auth_headers_alpha, auth_headers_beta, sample_jobs, resume_alpha, resume_beta, db
    ):
        job = sample_jobs[0]

        # User Alpha scores job with 95%
        with patch("app.services.match_service.GeminiClient") as MockGeminiA:
            MockGeminiA.return_value.match_job.return_value = {
                "match_score": 95,
                "missing_skills": [],
                "match_summary": "Alpha match.",
            }
            res_a = client.post(f"/api/jobs/{job.id}/score", headers=auth_headers_alpha)
            assert res_a.status_code == 200

        # User Beta scores job with 60%
        with patch("app.services.match_service.GeminiClient") as MockGeminiB:
            MockGeminiB.return_value.match_job.return_value = {
                "match_score": 60,
                "missing_skills": ["Python"],
                "match_summary": "Beta match.",
            }
            res_b = client.post(f"/api/jobs/{job.id}/score", headers=auth_headers_beta)
            assert res_b.status_code == 200

        # User Alpha force-rescores to 98%
        with patch("app.services.match_service.GeminiClient") as MockGeminiA2:
            MockGeminiA2.return_value.match_job.return_value = {
                "match_score": 98,
                "missing_skills": [],
                "match_summary": "Alpha updated.",
            }
            res_a2 = client.post(f"/api/jobs/{job.id}/score?force=true", headers=auth_headers_alpha)
            assert res_a2.status_code == 200

        # Check DB: User Alpha has 98, User Beta still has 60
        uj_alpha = db.scalar(select(UserJob).where(UserJob.job_id == job.id, UserJob.user_id == resume_alpha.user_id))
        uj_beta = db.scalar(select(UserJob).where(UserJob.job_id == job.id, UserJob.user_id == resume_beta.user_id))
        assert uj_alpha.match_score == 98
        assert uj_beta.match_score == 60
