"""
test_migration_hardening.py — Alembic migration safety tests.

Tests the hardened ownership and multi-user data isolation logic in:
`backend/alembic/versions/9d4e5f6a7b8c_multi_user_data_isolation.py`

Verifies the actual Alembic migration execution against PostgreSQL:
- Case A: Exactly 1 user (deterministic backfill of jobs, resumes, and scoring_runs)
- Case B: 0 users + legacy user-owned data (fails safely without data destruction)
- Case C: Multiple users + ambiguous legacy data (fails safely without arbitrary assignment)
- Case D: Multiple users + no user-specific legacy data (proceeds cleanly)
- Case E: Fresh / empty database (proceeds cleanly)
- Downgrade & Re-upgrade Reversibility (data restoration and schema integrity)
"""

from __future__ import annotations

import importlib.util
import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from tests.conftest import needs_db

pytestmark = needs_db

MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "9d4e5f6a7b8c_multi_user_data_isolation.py"
)


def _load_migration_module() -> Any:
    """Dynamically load the multi_user_data_isolation migration script."""
    spec = importlib.util.spec_from_file_location("migration_9d4e5f6a7b8c", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load migration module from {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration_module = _load_migration_module()


@pytest.fixture()
def isolated_schema(db_engine: Engine) -> Generator[tuple[Connection, str], None, None]:
    """
    Provide a dedicated, isolated PostgreSQL schema for testing Alembic migration logic.
    Sets search_path for the connection to the isolated schema and drops it on teardown.
    """
    schema_name = f"test_mig_{uuid.uuid4().hex[:8]}"
    connection = None
    for attempt in range(3):
        try:
            connection = db_engine.connect()
            break
        except Exception:
            if attempt == 2:
                raise
            import time
            time.sleep(0.5 * (attempt + 1))

    assert connection is not None
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    connection.execute(text(f'SET search_path TO "{schema_name}", public'))
    connection.commit()

    # Pre-migration schema at revision 8c3d4e5f6a7b
    # 1. jobs table with legacy user-specific columns
    connection.execute(text("""
        CREATE TABLE jobs (
            id UUID PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            company VARCHAR(500) NOT NULL,
            company_url TEXT,
            description TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            source VARCHAR(50) NOT NULL,
            location VARCHAR(200),
            posted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_seen_at TIMESTAMPTZ,
            missing_sync_count INTEGER NOT NULL DEFAULT 0,
            expired_at TIMESTAMPTZ,
            status VARCHAR(20) NOT NULL DEFAULT 'saved',
            notes TEXT,
            match_score INTEGER,
            missing_skills JSONB,
            match_summary TEXT,
            matched_at TIMESTAMPTZ,
            resume_uploaded_at TIMESTAMPTZ
        )
    """))
    connection.execute(text("CREATE INDEX idx_jobs_status ON jobs(status)"))
    connection.execute(text("CREATE INDEX idx_jobs_score ON jobs(match_score)"))

    # 2. users table (with Google OAuth fields)
    connection.execute(text("""
        CREATE TABLE users (
            id UUID PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            google_id VARCHAR(255),
            avatar_url TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    # 3. resumes table (pre-migration: no user_id)
    connection.execute(text("""
        CREATE TABLE resumes (
            id UUID PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            raw_text TEXT NOT NULL,
            skills JSONB NOT NULL DEFAULT '[]'::jsonb,
            uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    # 4. scoring_runs table (pre-migration: no user_id)
    connection.execute(text("""
        CREATE TABLE scoring_runs (
            id UUID PRIMARY KEY,
            total_jobs INTEGER NOT NULL DEFAULT 0,
            scored_jobs INTEGER NOT NULL DEFAULT 0,
            failed_jobs INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ
        )
    """))
    connection.commit()

    yield connection, schema_name

    connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
    connection.commit()
    connection.close()


def _run_upgrade(connection: Connection) -> None:
    """Execute the actual Alembic migration upgrade() within the connection's context."""
    ctx = MigrationContext.configure(connection)
    with Operations.context(ctx):
        migration_module.upgrade()
    connection.commit()


def _run_downgrade(connection: Connection) -> None:
    """Execute the actual Alembic migration downgrade() within the connection's context."""
    ctx = MigrationContext.configure(connection)
    with Operations.context(ctx):
        migration_module.downgrade()
    connection.commit()


class TestAlembicMigrationHardening:
    """Verification of Alembic migration 9d4e5f6a7b8c across all 5 edge cases and reversibility."""

    def test_case_a_one_user_deterministic_backfill(
        self, isolated_schema: tuple[Connection, str]
    ) -> None:
        """
        Case A: Exactly 1 registered user with multiple legacy jobs, resumes, and scoring runs.
        Verify:
        - Every legacy Job gets a UserJob record.
        - status='saved' jobs are preserved.
        - notes, match_score, missing_skills, match_summary, matched_at, resume_uploaded_at are preserved.
        - Existing resumes are assigned to the user.
        - Existing scoring_runs are assigned to the user.
        - Legacy user-specific columns are dropped from jobs.
        """
        conn, schema = isolated_schema
        user_id = uuid.uuid4()
        now = datetime.now(UTC)

        # 1. Insert 1 User
        conn.execute(
            text("""
                INSERT INTO users (id, email, name, password_hash, created_at, updated_at)
                VALUES (:uid, 'solo@example.com', 'Solo Founder', 'hash123', :now, :now)
            """),
            {"uid": user_id, "now": now},
        )

        # 2. Insert Multiple Legacy Jobs
        job_saved_id = uuid.uuid4()
        job_applied_id = uuid.uuid4()

        # Legacy job 1: saved status, no notes or scores
        conn.execute(
            text("""
                INSERT INTO jobs (
                    id, title, company, description, url, source,
                    status, created_at, updated_at
                )
                VALUES (
                    :jid, 'Junior Dev', 'Acme', 'Python role',
                    'https://jobs.example.com/junior', 'remoteok',
                    'saved', :now, :now
                )
            """),
            {"jid": job_saved_id, "now": now},
        )

        # Legacy job 2: applied status, full match details and notes
        skills_json = json.dumps(["Docker", "AWS", "Kubernetes"])
        conn.execute(
            text("""
                INSERT INTO jobs (
                    id, title, company, description, url, source,
                    status, notes, match_score, missing_skills,
                    match_summary, matched_at, resume_uploaded_at,
                    created_at, updated_at
                )
                VALUES (
                    :jid, 'Senior SRE', 'Cloud Corp', 'Infra role',
                    'https://jobs.example.com/sre', 'yc_jobs',
                    'applied', 'Referral from John', 88, CAST(:skills AS JSONB),
                    'Strong candidate with container experience', :now, :now,
                    :now, :now
                )
            """),
            {"jid": job_applied_id, "skills": skills_json, "now": now},
        )

        # 3. Insert Legacy Resume and ScoringRun without user_id
        resume_id = uuid.uuid4()
        scoring_run_id = uuid.uuid4()

        conn.execute(
            text("""
                INSERT INTO resumes (id, filename, raw_text, skills, uploaded_at)
                VALUES (:rid, 'resume.pdf', 'Python Developer', '["Python"]'::jsonb, :now)
            """),
            {"rid": resume_id, "now": now},
        )
        conn.execute(
            text("""
                INSERT INTO scoring_runs (id, total_jobs, scored_jobs, failed_jobs, status, created_at)
                VALUES (:srid, 2, 1, 0, 'completed', :now)
            """),
            {"srid": scoring_run_id, "now": now},
        )
        conn.commit()

        # Run actual migration upgrade
        _run_upgrade(conn)

        # Verify UserJob backfill for both jobs
        user_jobs = conn.execute(
            text("SELECT job_id, status, notes, match_score, missing_skills, match_summary, matched_at, resume_uploaded_at FROM user_jobs WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchall()
        assert len(user_jobs) == 2
        uj_dict = {row[0]: row for row in user_jobs}

        # Check job 1: status='saved' preserved
        saved_uj = uj_dict[job_saved_id]
        assert saved_uj[1] == "saved"
        assert saved_uj[2] is None  # notes
        assert saved_uj[3] is None  # match_score

        # Check job 2: all user data strictly preserved
        applied_uj = uj_dict[job_applied_id]
        assert applied_uj[1] == "applied"
        assert applied_uj[2] == "Referral from John"
        assert applied_uj[3] == 88
        assert applied_uj[4] == ["Docker", "AWS", "Kubernetes"]
        assert applied_uj[5] == "Strong candidate with container experience"
        assert applied_uj[6] is not None
        assert applied_uj[7] is not None

        # Verify resume assigned to single user
        assigned_resume = conn.execute(
            text("SELECT user_id FROM resumes WHERE id = :rid"),
            {"rid": resume_id},
        ).scalar()
        assert assigned_resume == user_id

        # Verify scoring_run assigned to single user
        assigned_run = conn.execute(
            text("SELECT user_id FROM scoring_runs WHERE id = :srid"),
            {"srid": scoring_run_id},
        ).scalar()
        assert assigned_run == user_id

        # Verify legacy columns dropped from jobs
        job_cols = [
            row[0]
            for row in conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_schema = :sch AND table_name = 'jobs'"),
                {"sch": schema},
            ).fetchall()
        ]
        assert "status" not in job_cols
        assert "notes" not in job_cols
        assert "match_score" not in job_cols
        assert "missing_skills" not in job_cols

    def test_case_b_zero_users_meaningful_legacy_aborts_safely(
        self, isolated_schema: tuple[Connection, str]
    ) -> None:
        """
        Case B: 0 users + legacy user-owned data.
        Verify migration:
        - aborts with a clear error
        - does NOT silently delete data
        - does NOT partially destroy legacy job data
        """
        conn, schema = isolated_schema
        now = datetime.now(UTC)
        job_id = uuid.uuid4()

        # Insert legacy job with meaningful state (interview status, custom notes, score)
        conn.execute(
            text("""
                INSERT INTO jobs (
                    id, title, company, description, url, source,
                    status, notes, match_score, match_summary, matched_at, resume_uploaded_at,
                    created_at, updated_at
                )
                VALUES (
                    :jid, 'Lead Architect', 'Apex', 'System design',
                    'https://jobs.example.com/arch', 'remoteok',
                    'interview', 'Screen scheduled for Monday', 95, 'Outstanding fit',
                    :now, :now, :now, :now
                )
            """),
            {"jid": job_id, "now": now},
        )
        conn.commit()

        # Attempt migration: must fail safely with clear error
        with pytest.raises(RuntimeError) as exc_info:
            _run_upgrade(conn)

        assert "Migration aborted: Found existing legacy data requiring ownership" in str(exc_info.value)
        assert "no user accounts exist in the 'users' table" in str(exc_info.value)

        # Verify data was NOT deleted and columns are NOT destroyed
        job_row = conn.execute(
            text("SELECT title, status, notes, match_score, match_summary FROM jobs WHERE id = :jid"),
            {"jid": job_id},
        ).fetchone()
        assert job_row is not None
        assert job_row[0] == "Lead Architect"
        assert job_row[1] == "interview"
        assert job_row[2] == "Screen scheduled for Monday"
        assert job_row[3] == 95
        assert job_row[4] == "Outstanding fit"

    def test_case_c_multiple_users_ambiguous_legacy_aborts_safely(
        self, isolated_schema: tuple[Connection, str]
    ) -> None:
        """
        Case C: Multiple users exist + unassigned legacy data.
        Verify migration:
        - aborts
        - does not arbitrarily select the first/oldest user
        - does not delete existing data
        - provides an actionable error
        """
        conn, schema = isolated_schema
        now = datetime.now(UTC)
        u1_id = uuid.uuid4()
        u2_id = uuid.uuid4()

        # Insert 2 users
        conn.execute(
            text("""
                INSERT INTO users (id, email, name, password_hash, created_at, updated_at)
                VALUES
                    (:u1, 'user1@example.com', 'User One', 'h1', :now, :now),
                    (:u2, 'user2@example.com', 'User Two', 'h2', :now, :now)
            """),
            {"u1": u1_id, "u2": u2_id, "now": now},
        )

        # Legacy job with meaningful state
        job_id = uuid.uuid4()
        conn.execute(
            text("""
                INSERT INTO jobs (
                    id, title, company, description, url, source,
                    status, notes, match_score, created_at, updated_at
                )
                VALUES (
                    :jid, 'Data Scientist', 'AI Corp', 'PyTorch role',
                    'https://jobs.example.com/ds', 'remoteok',
                    'offer', 'Accepted verbal offer', 94, :now, :now
                )
            """),
            {"jid": job_id, "now": now},
        )
        conn.commit()

        with pytest.raises(RuntimeError) as exc_info:
            _run_upgrade(conn)

        err_msg = str(exc_info.value)
        assert "Migration aborted: Found 2 users in the database and unassigned legacy data" in err_msg
        assert "Automatic backfill cannot safely determine data ownership among multiple users" in err_msg
        assert "Please manually assign user_id to existing records" in err_msg

        # Verify job and users still exist intact
        job_count = conn.execute(text("SELECT count(*) FROM jobs")).scalar()
        user_count = conn.execute(text("SELECT count(*) FROM users")).scalar()
        assert job_count == 1
        assert user_count == 2

    def test_case_d_multiple_users_no_legacy_user_data_proceeds(
        self, isolated_schema: tuple[Connection, str]
    ) -> None:
        """
        Case D: Multiple users exist + no legacy user-specific data (only raw scraped jobs).
        Verify migration can proceed when there is genuinely nothing requiring ownership backfill.
        """
        conn, schema = isolated_schema
        now = datetime.now(UTC)

        # Insert 2 users
        conn.execute(
            text("""
                INSERT INTO users (id, email, name, password_hash, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), 'u1@example.com', 'User 1', 'h1', :now, :now),
                    (gen_random_uuid(), 'u2@example.com', 'User 2', 'h2', :now, :now)
            """),
            {"now": now},
        )

        # Insert raw scraped jobs with default status='saved' and no user state
        conn.execute(
            text("""
                INSERT INTO jobs (
                    id, title, company, description, url, source,
                    status, notes, match_score, missing_skills, match_summary,
                    matched_at, resume_uploaded_at, created_at, updated_at
                )
                VALUES
                    (gen_random_uuid(), 'Job A', 'Comp A', 'Desc A', 'https://jobs.example.com/a', 'remoteok', 'saved', NULL, NULL, NULL, NULL, NULL, NULL, :now, :now),
                    (gen_random_uuid(), 'Job B', 'Comp B', 'Desc B', 'https://jobs.example.com/b', 'yc_jobs', 'saved', NULL, NULL, NULL, NULL, NULL, NULL, :now, :now)
            """),
            {"now": now},
        )
        conn.commit()

        # Must proceed without error
        _run_upgrade(conn)

        # user_jobs table exists and jobs columns are dropped
        uj_count = conn.execute(text("SELECT count(*) FROM user_jobs")).scalar()
        assert uj_count == 0  # No user state was backfilled

        job_cols = [
            row[0]
            for row in conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_schema = :sch AND table_name = 'jobs'"),
                {"sch": schema},
            ).fetchall()
        ]
        assert "status" not in job_cols
        assert "match_score" not in job_cols

    def test_case_e_fresh_empty_database_proceeds(
        self, isolated_schema: tuple[Connection, str]
    ) -> None:
        """
        Case E: Fresh / empty database (0 users, 0 jobs, 0 resumes, 0 scoring runs).
        Verify migration proceeds successfully without errors.
        """
        conn, schema = isolated_schema

        # Execute migration on completely empty database
        _run_upgrade(conn)

        tables = [
            row[0]
            for row in conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = :sch"),
                {"sch": schema},
            ).fetchall()
        ]
        assert "user_jobs" in tables
        assert "jobs" in tables
        assert "users" in tables
        assert "resumes" in tables
        assert "scoring_runs" in tables

    def test_downgrade_and_reupgrade_reversibility(
        self, isolated_schema: tuple[Connection, str]
    ) -> None:
        """
        Verify downgrade reversibly restores user_jobs state back into jobs,
        and upgrade succeeds again cleanly.
        """
        conn, schema = isolated_schema
        user_id = uuid.uuid4()
        job_id = uuid.uuid4()
        now = datetime.now(UTC)

        # 1. Setup 1 user and 1 legacy job with notes and score
        conn.execute(
            text("""
                INSERT INTO users (id, email, name, password_hash, created_at, updated_at)
                VALUES (:uid, 'revert@example.com', 'Revert Tester', 'pass', :now, :now)
            """),
            {"uid": user_id, "now": now},
        )
        conn.execute(
            text("""
                INSERT INTO jobs (
                    id, title, company, description, url, source,
                    status, notes, match_score, created_at, updated_at
                )
                VALUES (
                    :jid, 'Reversibility Engineer', 'Rollback Inc', 'Testing downgrades',
                    'https://jobs.example.com/rev', 'remoteok',
                    'applied', 'Initial notes', 85, :now, :now
                )
            """),
            {"jid": job_id, "now": now},
        )
        conn.commit()

        # 2. Upgrade to 9d4e5f6a7b8c
        _run_upgrade(conn)

        # Update the user_job with new notes
        conn.execute(
            text("UPDATE user_jobs SET notes = 'Updated note in user_jobs', status = 'interview' WHERE job_id = :jid"),
            {"jid": job_id},
        )
        conn.commit()

        # 3. Downgrade to 8c3d4e5f6a7b
        _run_downgrade(conn)

        # Check that user_jobs was dropped and legacy columns are restored on jobs
        downgraded_job = conn.execute(
            text("SELECT status, notes, match_score FROM jobs WHERE id = :jid"),
            {"jid": job_id},
        ).fetchone()
        assert downgraded_job is not None
        assert downgraded_job[0] == "interview"
        assert downgraded_job[1] == "Updated note in user_jobs"
        assert downgraded_job[2] == 85

        # Check user_jobs table does not exist
        uj_exists = conn.execute(
            text("SELECT count(*) FROM information_schema.tables WHERE table_schema = :sch AND table_name = 'user_jobs'"),
            {"sch": schema},
        ).scalar()
        assert uj_exists == 0

        # 4. Re-upgrade to 9d4e5f6a7b8c
        _run_upgrade(conn)

        # Re-upgraded state has user_jobs restored again
        reupgraded_uj = conn.execute(
            text("SELECT status, notes, match_score FROM user_jobs WHERE user_id = :uid AND job_id = :jid"),
            {"uid": user_id, "jid": job_id},
        ).fetchone()
        assert reupgraded_uj is not None
        assert reupgraded_uj[0] == "interview"
        assert reupgraded_uj[1] == "Updated note in user_jobs"
        assert reupgraded_uj[2] == 85
