"""
conftest.py — Test fixtures for Job Hunter backend.

Database strategy: PostgreSQL (required — JSONB and UUID types break SQLite).

Set TEST_DATABASE_URL env var to a live PostgreSQL DSN before running:
    export TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/test_db"

All DB tests are skipped automatically when TEST_DATABASE_URL is absent.

Fixture hierarchy:
    engine (session-scoped)  — creates all tables once
      └─ db (function-scoped) — transaction rolled back after each test
           └─ job_service / resume_service / scraper_service / match_service

External mocks (always active, no real network calls):
    mock_gemini   — patches GeminiClient at app.ai.gemini_client.GeminiClient
    mock_scraper  — a fake BaseScraper implementation
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.resume import Resume
    from app.schemas.job import JobUpsertData
    from app.services.job_service import JobService
    from app.services.resume_service import ResumeService
    from app.services.scraper_service import ScraperService

# Load environment variables from .env file if present
load_dotenv()

# ---------------------------------------------------------------------------
# Skip marker & safety guard — canonical PostgreSQL test DB validation
# ---------------------------------------------------------------------------

_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL")

needs_db = pytest.mark.skipif(
    not _TEST_DB_URL,
    reason="TEST_DATABASE_URL environment variable is not set",
)


def validate_test_database_url(url_str: str) -> None:
    """
    Strict safety guard verifying TEST_DATABASE_URL connects to PostgreSQL
    and specifies a dedicated test database name (must contain 'test').
    """
    if not url_str or not url_str.strip():
        raise ValueError("TEST_DATABASE_URL environment variable is empty or unset.")

    parsed = make_url(url_str)

    if not parsed.drivername.startswith("postgresql"):
        raise ValueError(
            f"TEST_DATABASE_URL must be a PostgreSQL connection string (got '{parsed.drivername}'). "
            "SQLite and non-PostgreSQL databases are not supported for tests."
        )

    db_name = parsed.database
    if not db_name or "test" not in db_name.lower():
        raise ValueError(
            f"Refusing to run tests against non-test database '{db_name}'. "
            "Database name must contain 'test' (e.g., 'test_db')."
        )


# ---------------------------------------------------------------------------
# Database engine (session-scoped — tables created once per test session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """
    Create a SQLAlchemy engine bound to TEST_DATABASE_URL.

    Validates PostgreSQL connection string and database safety guard before running.
    Uses NullPool for reliable cloud and local PostgreSQL test connections.
    Creates all ORM tables before tests run; drops engine on teardown.
    """
    if not _TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL environment variable is not set")

    validate_test_database_url(_TEST_DB_URL)

    # Import all models so their tables are registered on Base.metadata
    import app.models.job  # noqa: F401
    import app.models.resume  # noqa: F401
    import app.models.scoring_run  # noqa: F401
    import app.models.scrape_run  # noqa: F401
    import app.models.user  # noqa: F401
    import app.models.user_job  # noqa: F401
    from app.database import Base  # noqa: PLC0415

    engine = create_engine(
        _TEST_DB_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    )

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


# ---------------------------------------------------------------------------
# Per-test transactional session (rolled back after each test)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(db_engine: Engine) -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy Session wrapped in a savepoint.

    All changes made during a test are rolled back on teardown —
    each test starts with a clean database state.
    """
    connection = db_engine.connect()
    trans = connection.begin()

    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        if trans.is_active:
            with suppress(Exception):
                trans.rollback()
        connection.close()


# ---------------------------------------------------------------------------
# ORM object factories
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_user(db: Session):
    from app.models.user import User  # noqa: PLC0415

    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
        password_hash="test-password-hash",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def auth_headers(sample_user) -> dict[str, str]:
    from app.core.security import create_access_token  # noqa: PLC0415

    token = create_access_token({"sub": str(sample_user.id), "email": sample_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_job(db: Session) -> Job:
    """
    Insert and return a minimal valid Job ORM instance.
    """
    from app.models.job import Job  # noqa: PLC0415

    job = Job(
        id=uuid.uuid4(),
        title="Backend Engineer",
        company="Acme Corp",
        description="Build APIs with FastAPI and PostgreSQL.",
        url=f"https://example.com/jobs/backend-{uuid.uuid4().hex[:6]}",
        source="remoteok",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture()
def scored_job(db: Session, sample_user) -> Job:
    """
    Insert and return a Job that has already been scored for sample_user.
    """
    from app.models.job import Job  # noqa: PLC0415
    from app.models.user_job import UserJob  # noqa: PLC0415

    now = datetime.now(UTC)
    job = Job(
        id=uuid.uuid4(),
        title="ML Engineer",
        company="DeepMind",
        description="Research and productionise ML models.",
        url=f"https://example.com/jobs/ml-{uuid.uuid4().hex[:6]}",
        source="yc_jobs",
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()

    user_job = UserJob(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        job_id=job.id,
        status="saved",
        match_score=82,
        missing_skills=["Rust", "CUDA"],
        match_summary="Strong Python fit. Missing low-level skills.",
        matched_at=now,
        resume_uploaded_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(user_job)
    db.commit()
    db.refresh(job)

    # Attach convenience attributes for tests expecting them
    job.status = user_job.status
    job.match_score = user_job.match_score
    job.resume_uploaded_at = user_job.resume_uploaded_at
    return job


@pytest.fixture()
def sample_resume(db: Session, sample_user) -> Resume:
    """
    Insert and return a minimal valid Resume ORM instance for sample_user.
    """
    from app.models.resume import Resume  # noqa: PLC0415

    resume = Resume(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        filename="john_doe_resume.pdf",
        raw_text="Python FastAPI PostgreSQL React TypeScript " * 10,
        skills=["Python", "FastAPI", "PostgreSQL", "React", "TypeScript"],
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


# ---------------------------------------------------------------------------
# Service fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def job_service(db: Session, sample_user) -> JobService:
    from app.services.job_service import JobService  # noqa: PLC0415
    return JobService(db, user_id=sample_user.id)


@pytest.fixture()
def resume_service(db: Session, sample_user) -> ResumeService:
    from app.services.resume_service import ResumeService  # noqa: PLC0415
    return ResumeService(db, user_id=sample_user.id)


@pytest.fixture()
def scraper_service(db: Session, sample_user) -> ScraperService:
    from app.services.scraper_service import ScraperService  # noqa: PLC0415
    return ScraperService(db, user_id=sample_user.id)


# ---------------------------------------------------------------------------
# External dependency mocks
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_gemini() -> Generator[MagicMock, None, None]:
    """
    Patch GeminiClient at its definition module so all imports see the mock.

    Returns the MagicMock instance pre-configured with sensible defaults:
      - extract_skills()  → ["Python", "FastAPI"]
      - match_job()       → MatchResult dict
    """
    with patch("app.ai.gemini_client.GeminiClient") as MockClass:
        instance: MagicMock = MockClass.return_value
        instance.extract_skills.return_value = ["Python", "FastAPI"]
        instance.match_job.return_value = {
            "match_score": 75,
            "missing_skills": ["Docker", "Kubernetes"],
            "match_summary": "Good Python fit. Missing container skills.",
        }
        yield instance


@pytest.fixture()
def mock_fitz() -> Generator[MagicMock, None, None]:
    """
    Patch fitz (PyMuPDF) so PDF extraction works without a real PDF.

    Sets up a minimal document/page structure returning predictable text.
    """
    fake_text = "Software Engineer with Python FastAPI experience. " * 10

    with patch("app.services.resume_service.fitz") as mock_fitz_module:
        # Build mock page
        mock_page = MagicMock()
        mock_page.get_text.return_value = fake_text

        # Build mock document
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2
        mock_doc.is_encrypted = False
        mock_doc.__getitem__.return_value = mock_page

        # fitz.open(...) returns the mock doc
        mock_fitz_module.open.return_value = mock_doc

        yield mock_fitz_module


class FakeScraper:
    """
    Minimal BaseScraper-compatible stub for scraper_service tests.

    Returns two deterministic JobUpsertData objects when run() is called.
    Configurable: set .raises to an Exception to simulate failure.
    """

    def __init__(self, source: str = "remoteok", *, raises: Exception | None = None) -> None:
        self.source = source
        self.raises = raises
        self._jobs_returned: list[JobUpsertData] = []

    def set_jobs(self, jobs: list[JobUpsertData]) -> None:
        self._jobs_returned = jobs

    def run(self) -> list[JobUpsertData]:
        if self.raises is not None:
            raise self.raises
        return self._jobs_returned


@pytest.fixture()
def fake_scraper() -> FakeScraper:
    """Return a FakeScraper pre-loaded with two jobs."""
    from app.schemas.job import JobUpsertData  # noqa: PLC0415

    scraper = FakeScraper(source="remoteok")
    scraper.set_jobs([
        JobUpsertData(
            title="Backend Engineer",
            company="Acme",
            description="Build APIs",
            url="https://jobs.example.com/1",
            source="remoteok",
        ),
        JobUpsertData(
            title="Frontend Engineer",
            company="Globex",
            description="Build UIs",
            url="https://jobs.example.com/2",
            source="remoteok",
        ),
    ])
    return scraper


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient fixture with overridden DB session.
    """
    from app.database import get_db  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415

    def _override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)