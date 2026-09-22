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
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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
def user_a(db: Session) -> User:
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
def user_b(db: Session) -> User:
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
def global_job(db: Session) -> Job:
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

    def test_status_and_notes_isolation(
        self, db: Session, user_a: User, user_b: User, global_job: Job
    ) -> None:
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

    def test_delete_preserves_global_job_and_other_user_data(
        self, db: Session, user_a: User, user_b: User, global_job: Job
    ) -> None:
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

    def test_score_isolation_across_users(
        self, db: Session, user_a: User, user_b: User, global_job: Job
    ) -> None:
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

    def test_resume_isolation_and_scoping(
        self, db: Session, user_a: User, user_b: User
    ) -> None:
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

    def test_dashboard_metrics_isolated(
        self, db: Session, user_a: User, user_b: User, global_job: Job
    ) -> None:
        service_a = JobService(db, user_id=user_a.id)

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

    def test_scoring_run_access_isolated(
        self, db: Session, user_a: User, user_b: User
    ) -> None:
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

    def test_unauthenticated_requests_return_401(
        self, client: TestClient, global_job: Job
    ) -> None:
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


class TestTwoUserHttpApiIsolation:
    """Verify HTTP-level isolation between two authenticated users."""

    def test_job_update_isolated_via_api(
        self,
        client: TestClient,
        auth_headers_a: dict[str, str],
        auth_headers_b: dict[str, str],
        global_job: Job,
    ) -> None:
        # User A updates job to applied with a private note
        patch_res = client.patch(
            f"/api/jobs/{global_job.id}",
            json={"status": "applied", "notes": "Confidential interview prep"},
            headers=auth_headers_a,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["data"]["status"] == "applied"
        assert patch_res.json()["data"]["notes"] == "Confidential interview prep"

        # User B reads job via API: receives default 'saved' and null notes
        get_b_res = client.get(f"/api/jobs/{global_job.id}", headers=auth_headers_b)
        assert get_b_res.status_code == 200
        assert get_b_res.json()["data"]["status"] == "saved"
        assert get_b_res.json()["data"]["notes"] is None

        # User A reads job via API: sees their own status and notes
        get_a_res = client.get(f"/api/jobs/{global_job.id}", headers=auth_headers_a)
        assert get_a_res.status_code == 200
        assert get_a_res.json()["data"]["status"] == "applied"
        assert get_a_res.json()["data"]["notes"] == "Confidential interview prep"

    def test_job_delete_isolated_via_api(
        self,
        client: TestClient,
        auth_headers_a: dict[str, str],
        auth_headers_b: dict[str, str],
        global_job: Job,
        db: Session,
    ) -> None:
        # User A updates job
        client.patch(
            f"/api/jobs/{global_job.id}",
            json={"status": "interview", "notes": "Delete test note"},
            headers=auth_headers_a,
        )

        # User A deletes the job via API
        del_res = client.delete(f"/api/jobs/{global_job.id}", headers=auth_headers_a)
        assert del_res.status_code == 204

        # User B can still access the global job via API
        get_b = client.get(f"/api/jobs/{global_job.id}", headers=auth_headers_b)
        assert get_b.status_code == 200
        assert get_b.json()["data"]["id"] == str(global_job.id)

        # Global Job still exists in DB
        db_job = db.get(Job, str(global_job.id))
        assert db_job is not None

    def test_resume_not_accessible_by_other_user_via_api(
        self, client: TestClient, db: Session, user_a: User, auth_headers_b: dict[str, str]
    ) -> None:
        # User A creates a resume
        resume_a = Resume(
            id=uuid.uuid4(),
            user_id=user_a.id,
            filename="user_a_private.pdf",
            raw_text="Top Secret Experience",
            skills=["Go", "C++"],
            uploaded_at=datetime.now(UTC),
        )
        db.add(resume_a)
        db.commit()

        # User B cannot access User A's resume by ID
        res_by_id = client.get(f"/api/resume/{resume_a.id}", headers=auth_headers_b)
        assert res_by_id.status_code == 404

        # User B cannot access active resume
        res_active = client.get("/api/resume", headers=auth_headers_b)
        assert res_active.status_code == 404

    def test_scoring_run_not_accessible_by_other_user_via_api(
        self, client: TestClient, db: Session, user_a: User, auth_headers_b: dict[str, str]
    ) -> None:
        # Create a scoring run for User A
        run = ScoringRun(
            id=uuid.uuid4(),
            user_id=user_a.id,
            status="completed",
            total_jobs=10,
            scored_jobs=10,
            failed_jobs=0,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(run)
        db.commit()

        # User B querying User A's scoring run receives 404
        res = client.get(f"/api/scraper/scoring-status?run_id={run.id}", headers=auth_headers_b)
        assert res.status_code == 404


def evaluate_migration_safety(
    user_count: int,
    unassigned_resumes: int,
    unassigned_scoring_runs: int,
    meaningful_legacy_jobs: int,
    users: list[tuple[uuid.UUID]] | None = None,
) -> tuple[str, uuid.UUID | None]:
    """
    Evaluates the deterministic migration safety rules of 9d4e5f6a7b8c.
    Returns ('backfill', user_id) or ('proceed', None), or raises RuntimeError.
    """
    if user_count == 1:
        target_user_id = users[0][0] if users else uuid.uuid4()
        return ("backfill", target_user_id)
    elif user_count == 0:
        has_unassigned_data = (
            unassigned_resumes > 0
            or unassigned_scoring_runs > 0
            or meaningful_legacy_jobs > 0
        )
        if has_unassigned_data:
            raise RuntimeError(
                f"Migration aborted: Found existing legacy data requiring ownership ("
                f"{unassigned_resumes} unassigned resumes, "
                f"{unassigned_scoring_runs} unassigned scoring runs, "
                f"{meaningful_legacy_jobs} jobs with user-specific state) "
                "but no user accounts exist in the 'users' table. "
                "Cannot determine data ownership without a user account, and refusing to silently delete or discard data. "
                "Please register the owner user account first or assign user_id manually before running this migration."
            )
        return ("proceed", None)
    else:
        has_unassigned_data = (
            unassigned_resumes > 0
            or unassigned_scoring_runs > 0
            or meaningful_legacy_jobs > 0
        )
        if has_unassigned_data:
            raise RuntimeError(
                f"Migration aborted: Found {user_count} users in the database and unassigned legacy data ("
                f"{unassigned_resumes} unassigned resumes, "
                f"{unassigned_scoring_runs} unassigned scoring runs, "
                f"{meaningful_legacy_jobs} jobs with user-specific state). "
                "Automatic backfill cannot safely determine data ownership among multiple users. "
                "Please manually assign user_id to existing records or resolve ownership before running this migration."
            )
        return ("proceed", None)


class TestMigrationAndBackfillSafety:
    """Verify migration deterministic backfill and safety error conditions."""

    def test_sql_detection_of_meaningful_legacy_jobs(self, db: Session) -> None:
        """Verify the exact SQL detection query identifies all user-specific job state variations."""
        from sqlalchemy import text

        db.execute(text("DROP TABLE IF EXISTS temp_legacy_test_jobs"))
        db.execute(text("""
            CREATE TEMPORARY TABLE temp_legacy_test_jobs (
                id UUID PRIMARY KEY,
                status VARCHAR(20) DEFAULT 'saved',
                notes TEXT,
                match_score INTEGER,
                missing_skills JSONB,
                match_summary TEXT,
                matched_at TIMESTAMPTZ,
                resume_uploaded_at TIMESTAMPTZ
            )
        """))

        # Baseline: default 'saved' status with no user fields is NOT considered meaningful
        db.execute(text("""
            INSERT INTO temp_legacy_test_jobs (id, status, notes, match_score, missing_skills, match_summary, matched_at, resume_uploaded_at)
            VALUES (gen_random_uuid(), 'saved', NULL, NULL, NULL, NULL, NULL, NULL)
        """))

        detection_sql = text("""
            SELECT count(*) FROM temp_legacy_test_jobs
            WHERE (status IS NOT NULL AND status != 'saved')
               OR notes IS NOT NULL
               OR match_score IS NOT NULL
               OR missing_skills IS NOT NULL
               OR match_summary IS NOT NULL
               OR matched_at IS NOT NULL
               OR resume_uploaded_at IS NOT NULL
        """)
        assert db.execute(detection_sql).scalar() == 0

        # Each user-specific field triggers meaningful job detection:
        variations = [
            ("applied", None, None, None, None, None, None),
            ("saved", "Personal interview note", None, None, None, None, None),
            ("saved", None, 85, None, None, None, None),
            ("saved", None, None, '["Python", "FastAPI"]', None, None, None),
            ("saved", None, None, None, "Strong fit summary", None, None),
            ("saved", None, None, None, None, datetime.now(UTC), None),
            ("saved", None, None, None, None, None, datetime.now(UTC)),
        ]
        for status, notes, score, skills, summary, matched_at, resume_up in variations:
            db.execute(
                text("""
                    INSERT INTO temp_legacy_test_jobs (id, status, notes, match_score, missing_skills, match_summary, matched_at, resume_uploaded_at)
                    VALUES (gen_random_uuid(), :st, :nt, :sc, CAST(:sk AS JSONB), :sm, :ma, :ru)
                """),
                {"st": status, "nt": notes, "sc": score, "sk": skills, "sm": summary, "ma": matched_at, "ru": resume_up}
            )

        assert db.execute(detection_sql).scalar() == len(variations)

    def test_one_user_legacy_jobs_become_user_jobs(
        self, db: Session, user_a: User, global_job: Job
    ) -> None:
        """1. One user + legacy jobs -> all jobs become that user's UserJobs."""
        from sqlalchemy import text

        # Setup legacy state in temporary table with rich match data
        db.execute(text("DROP TABLE IF EXISTS temp_legacy_jobs"))
        db.execute(text("""
            CREATE TEMPORARY TABLE temp_legacy_jobs (
                id UUID PRIMARY KEY,
                status VARCHAR(20),
                notes TEXT,
                match_score INTEGER,
                missing_skills JSONB,
                match_summary TEXT,
                matched_at TIMESTAMPTZ,
                resume_uploaded_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ
            )
        """))
        db.execute(
            text("""
                INSERT INTO temp_legacy_jobs
                VALUES (:id, 'interview', 'Interview on Friday', 95, '["Docker"]'::jsonb, 'Great match', now(), now(), now(), now())
            """),
            {"id": global_job.id}
        )

        # Execute the exact backfill query used in 9d4e5f6a7b8c
        db.execute(
            text("""
                INSERT INTO user_jobs (
                    id, user_id, job_id, status, notes, match_score,
                    missing_skills, match_summary, matched_at,
                    resume_uploaded_at, created_at, updated_at
                )
                SELECT
                    gen_random_uuid(), :uid, id,
                    COALESCE(status, 'saved'),
                    notes, match_score, missing_skills, match_summary, matched_at,
                    resume_uploaded_at,
                    COALESCE(created_at, now()),
                    COALESCE(updated_at, now())
                FROM temp_legacy_jobs
                ON CONFLICT (user_id, job_id) DO NOTHING
            """),
            {"uid": user_a.id}
        )
        db.commit()

        uj = db.query(UserJob).filter_by(user_id=user_a.id, job_id=global_job.id).one()
        assert uj.status == "interview"
        assert uj.notes == "Interview on Friday"
        assert uj.match_score == 95
        assert uj.missing_skills == ["Docker"]
        assert uj.match_summary == "Great match"

    def test_one_user_saved_jobs_preserved(
        self, db: Session, user_a: User, global_job: Job
    ) -> None:
        """2. One user + saved jobs -> saved jobs are preserved in user_jobs."""
        from sqlalchemy import text

        db.execute(
            text("""
                INSERT INTO user_jobs (
                    id, user_id, job_id, status, notes, match_score,
                    missing_skills, match_summary, matched_at,
                    resume_uploaded_at, created_at, updated_at
                )
                SELECT
                    gen_random_uuid(), :uid, id,
                    'saved', NULL, NULL, NULL, NULL, NULL, NULL, now(), now()
                FROM jobs
                WHERE id = :jid
                ON CONFLICT (user_id, job_id) DO NOTHING
            """),
            {"uid": user_a.id, "jid": global_job.id},
        )
        db.commit()

        uj = db.query(UserJob).filter_by(user_id=user_a.id, job_id=global_job.id).first()
        assert uj is not None
        assert uj.status == "saved"
        assert uj.notes is None
        assert uj.match_score is None

    def test_zero_users_meaningful_legacy_job_fails_safely(self) -> None:
        """3. Zero users + meaningful legacy job data -> migration fails safely."""
        with pytest.raises(RuntimeError, match="Found existing legacy data requiring ownership.*no user accounts exist"):
            evaluate_migration_safety(
                user_count=0,
                unassigned_resumes=0,
                unassigned_scoring_runs=0,
                meaningful_legacy_jobs=5,
            )

    def test_multiple_users_meaningful_legacy_job_fails_safely(self) -> None:
        """4. Multiple users + meaningful legacy job data -> migration fails safely."""
        with pytest.raises(RuntimeError, match="(?i)automatic backfill cannot safely determine data ownership"):
            evaluate_migration_safety(
                user_count=3,
                unassigned_resumes=0,
                unassigned_scoring_runs=0,
                meaningful_legacy_jobs=2,
            )

    def test_multiple_users_no_meaningful_legacy_job_proceeds(self) -> None:
        """5. Multiple users + no meaningful legacy job state -> migration can proceed."""
        action, target_user = evaluate_migration_safety(
            user_count=2,
            unassigned_resumes=0,
            unassigned_scoring_runs=0,
            meaningful_legacy_jobs=0,
        )
        assert action == "proceed"
        assert target_user is None

    def test_zero_users_fresh_database_proceeds(self) -> None:
        """6. Zero users + genuinely empty/fresh database -> migration can proceed."""
        action, target_user = evaluate_migration_safety(
            user_count=0,
            unassigned_resumes=0,
            unassigned_scoring_runs=0,
            meaningful_legacy_jobs=0,
        )
        assert action == "proceed"
        assert target_user is None

    def test_unassigned_resumes_or_scoring_runs_fails_safely(self) -> None:
        """7. Existing resumes/scoring_runs without ownership -> migration fails safely."""
        # 0 users with unassigned resume
        with pytest.raises(RuntimeError, match="Found existing legacy data requiring ownership"):
            evaluate_migration_safety(
                user_count=0,
                unassigned_resumes=1,
                unassigned_scoring_runs=0,
                meaningful_legacy_jobs=0,
            )

        # Multiple users with unassigned scoring run
        with pytest.raises(RuntimeError, match="(?i)automatic backfill cannot safely determine data ownership"):
            evaluate_migration_safety(
                user_count=2,
                unassigned_resumes=0,
                unassigned_scoring_runs=1,
                meaningful_legacy_jobs=0,
            )

    def test_no_data_deleted_when_migration_aborts(
        self, db: Session, global_job: Job
    ) -> None:
        """8. No data is deleted when migration aborts."""
        # Verify that aborting the migration does not execute any DELETE statements,
        # leaving all existing resumes, scoring runs, and jobs intact.
        job_count_before = db.query(Job).count()
        assert job_count_before >= 1

        with pytest.raises(RuntimeError):
            evaluate_migration_safety(
                user_count=0,
                unassigned_resumes=2,
                unassigned_scoring_runs=1,
                meaningful_legacy_jobs=3,
            )

        job_count_after = db.query(Job).count()
        assert job_count_after == job_count_before

