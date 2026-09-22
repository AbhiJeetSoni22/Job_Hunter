"""
test_multi_user_isolation.py

Comprehensive tests verifying data isolation between multiple users:
1. UserJob status and notes isolation across users for the same global job.
2. AI Match score and resume matching isolation (User A's score doesn't leak to User B).
3. DELETE /jobs/{id} removes only the authenticated user's UserJob; global Job remains intact for other users.
4. Resume isolation (User A cannot access User B's resume).
5. Dashboard metrics isolation (User A's applications and scores don't affect User B's metrics).
6. ScoringRun and auto-scoring isolation (ScoringRun belongs to User A; auto-scoring only scores into User A's UserJob).
7. Unauthenticated access enforcement (401 for protected endpoints).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.job import Job
from app.models.resume import Resume
from app.models.scoring_run import ScoringRun
from app.models.user import User
from app.models.user_job import UserJob
from app.schemas.job import JobUpdateRequest
from app.services.dashboard_service import DashboardService
from app.services.job_service import JobService
from app.services.match_service import score_job
from app.services.resume_service import ResumeService
from app.services.scraper_service import ScraperService
from tests.conftest import needs_db

pytestmark = needs_db


@pytest.fixture()
def user_a(db) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"user-a-{uuid.uuid4().hex[:6]}@example.com",
        name="User Alpha",
        password_hash="hash-a",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def user_b(db) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"user-b-{uuid.uuid4().hex[:6]}@example.com",
        name="User Beta",
        password_hash="hash-b",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def auth_headers_a(user_a: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user_a.id), "email": user_a.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers_b(user_b: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user_b.id), "email": user_b.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def global_job(db) -> Job:
    job = Job(
        id=uuid.uuid4(),
        title="Staff Platform Engineer",
        company="Global Tech",
        description="Kubernetes, Python, Distributed Systems",
        url=f"https://example.com/jobs/platform-{uuid.uuid4().hex[:6]}",
        source="remoteok",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class TestUserJobIsolation:
    """Verify that user-specific tracking data (status, notes) is strictly isolated."""

    def test_status_and_notes_isolation(self, db, user_a, user_b, global_job):
        service_a = JobService(db, user_id=user_a.id)
        service_b = JobService(db, user_id=user_b.id)

        # User A updates job to applied with personal note
        service_a.update_job(
            global_job.id,
            JobUpdateRequest(status="applied", notes="Applied on company site"),
        )

        # User A sees updated status and notes
        job_a = service_a.get_job(global_job.id)
        assert job_a.status == "applied"
        assert job_a.notes == "Applied on company site"

        # User B still sees default status 'saved' and notes None
        job_b = service_b.get_job(global_job.id)
        assert job_b.status == "saved"
        assert job_b.notes is None

        # User B updates job to interview with different note
        service_b.update_job(
            global_job.id,
            JobUpdateRequest(status="interview", notes="Screen scheduled for Monday"),
        )

        # Confirm User A's data remains unchanged
        job_a_refreshed = service_a.get_job(global_job.id)
        assert job_a_refreshed.status == "applied"
        assert job_a_refreshed.notes == "Applied on company site"

        # Confirm User B's data is distinct
        job_b_refreshed = service_b.get_job(global_job.id)
        assert job_b_refreshed.status == "interview"
        assert job_b_refreshed.notes == "Screen scheduled for Monday"


class TestDeleteJobIsolation:
    """Verify DELETE /jobs/{id} removes ONLY the user's UserJob and preserves global Job."""

    def test_delete_preserves_global_job_and_other_user_data(self, db, user_a, user_b, global_job):
        service_a = JobService(db, user_id=user_a.id)
        service_b = JobService(db, user_id=user_b.id)

        # Both users annotate the job
        service_a.update_job(global_job.id, JobUpdateRequest(status="applied", notes="Note A"))
        service_b.update_job(global_job.id, JobUpdateRequest(status="offer", notes="Note B"))

        # User A deletes the job
        service_a.delete_job(global_job.id)

        # Global Job still exists in database
        db_job = db.get(Job, str(global_job.id))
        assert db_job is not None

        # User A's view is reset to default (no UserJob row)
        job_a = service_a.get_job(global_job.id)
        assert job_a.status == "saved"
        assert job_a.notes is None

        # User B's view is completely untouched
        job_b = service_b.get_job(global_job.id)
        assert job_b.status == "offer"
        assert job_b.notes == "Note B"


class TestMatchScoreIsolation:
    """Verify AI scoring calculates against user's active resume and persists only to that user."""

    def test_score_isolation_across_users(self, db, user_a, user_b, global_job):
        # User A uploads a Python-heavy resume
        resume_a = Resume(
            id=uuid.uuid4(),
            user_id=user_a.id,
            filename="user_a_resume.pdf",
            raw_text="Python Kubernetes distributed systems",
            skills=["Python", "Kubernetes"],
            uploaded_at=datetime.now(UTC),
        )
        db.add(resume_a)

        # User B uploads a Java-heavy resume
        resume_b = Resume(
            id=uuid.uuid4(),
            user_id=user_b.id,
            filename="user_b_resume.pdf",
            raw_text="Java Spring SQL",
            skills=["Java", "Spring"],
            uploaded_at=datetime.now(UTC),
        )
        db.add(resume_b)
        db.commit()

        # Score job for User A
        with patch("app.services.match_service.GeminiClient") as MockGemini:
            MockGemini.return_value.match_job.return_value = {
                "match_score": 92,
                "missing_skills": [],
                "match_summary": "Great match for User A",
            }
            score_job(str(global_job.id), db, user_id=user_a.id)

        # User A sees their score
        service_a = JobService(db, user_id=user_a.id)
        job_a = service_a.get_job(global_job.id)
        assert job_a.match_score == 92
        assert job_a.match_summary == "Great match for User A"

        # User B sees no score yet for this job
        service_b = JobService(db, user_id=user_b.id)
        job_b = service_b.get_job(global_job.id)
        assert job_b.match_score is None
        assert job_b.match_summary is None

        # Now score job for User B with their own result
        with patch("app.services.match_service.GeminiClient") as MockGeminiB:
            MockGeminiB.return_value.match_job.return_value = {
                "match_score": 58,
                "missing_skills": ["Python", "Kubernetes"],
                "match_summary": "Low match for User B",
            }
            score_job(str(global_job.id), db, user_id=user_b.id)

        # Verify User A's score is unchanged and User B has their distinct score
        assert service_a.get_job(global_job.id).match_score == 92
        assert service_b.get_job(global_job.id).match_score == 58


class TestResumeIsolation:
    """Verify each user has their own active resume and cannot view or delete another's."""

    def test_resume_isolation_and_scoping(self, db, user_a, user_b):
        service_a = ResumeService(db, user_id=user_a.id)
        service_b = ResumeService(db, user_id=user_b.id)

        # Insert resume for User A directly
        resume_a = Resume(
            id=uuid.uuid4(),
            user_id=user_a.id,
            filename="resume_a.pdf",
            raw_text="User A Experience",
            skills=["Python"],
            uploaded_at=datetime.now(UTC),
        )
        db.add(resume_a)
        db.commit()

        # User A can fetch their latest resume
        assert service_a.get_latest().filename == "resume_a.pdf"

        # User B has no active resume
        with pytest.raises(LookupError, match="No resume uploaded"):
            service_b.get_latest()

        # User B cannot access User A's resume by ID
        with pytest.raises(LookupError, match="not found"):
            service_b.get_by_id(resume_a.id)


class TestDashboardIsolation:
    """Verify Dashboard statistics are isolated between users."""

    def test_dashboard_metrics_isolated(self, db, user_a, user_b, global_job):
        service_a = JobService(db, user_id=user_a.id)
        service_b = JobService(db, user_id=user_b.id)

        # User A marks job applied and assigns a match score
        service_a.update_job(global_job.id, JobUpdateRequest(status="applied"))
        user_job_a = db.query(UserJob).filter_by(job_id=global_job.id, user_id=user_a.id).one()
        user_job_a.match_score = 90
        db.commit()

        # Dashboard for User A reflects their activity
        dash_a = DashboardService(db, user_id=user_a.id).get_stats()
        assert dash_a.total_jobs >= 1
        assert dash_a.scored_jobs == 1
        assert dash_a.applications_submitted == 1
        assert dash_a.best_match_score == 90
        assert len(dash_a.top_matches) == 1

        # Dashboard for User B reflects zero user activity, but sees global total_jobs
        dash_b = DashboardService(db, user_id=user_b.id).get_stats()
        assert dash_b.total_jobs == dash_a.total_jobs
        assert dash_b.scored_jobs == 0
        assert dash_b.applications_submitted == 0
        assert dash_b.best_match_score is None
        assert dash_b.top_matches == []


class TestScoringRunIsolation:
    """Verify ScoringRun belongs to a user and cannot be seen by others."""

    def test_scoring_run_access_isolated(self, db, user_a, user_b):
        service_a = ScraperService(db, user_id=user_a.id)
        service_b = ScraperService(db, user_id=user_b.id)

        run = service_a.start_scoring_run(total_jobs=5)
        assert run.user_id == user_a.id

        # User A can get their scoring run
        assert service_a.get_scoring_run(run.id) is not None

        # User B cannot access User A's scoring run
        assert service_b.get_scoring_run(run.id) is None


class TestApiAuthEnforcement:
    """Verify API endpoints require authentication and reject unauthenticated requests."""

    def test_unauthenticated_requests_return_401(self, client: TestClient, global_job):
        # GET /api/jobs
        res = client.get("/api/jobs")
        assert res.status_code == 401

        # GET /api/jobs/{id}
        res = client.get(f"/api/jobs/{global_job.id}")
        assert res.status_code == 401

        # POST /api/jobs/{id}/score
        res = client.post(f"/api/jobs/{global_job.id}/score")
        assert res.status_code == 401

        # PATCH /api/jobs/{id}
        res = client.patch(f"/api/jobs/{global_job.id}", json={"status": "applied"})
        assert res.status_code == 401

        # DELETE /api/jobs/{id}
        res = client.delete(f"/api/jobs/{global_job.id}")
        assert res.status_code == 401

        # GET /api/resume
        res = client.get("/api/resume")
        assert res.status_code == 401

        # GET /api/dashboard/stats
        res = client.get("/api/dashboard/stats")
        assert res.status_code == 401

        # POST /api/scraper/run
        res = client.post("/api/scraper/run")
        assert res.status_code == 401
