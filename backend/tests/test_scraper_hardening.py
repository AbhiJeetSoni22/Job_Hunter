"""
test_scraper_hardening.py

Comprehensive tests for Phase 0 Batch 2: Scraper Correctness & Safety.

Verifies:
1. Successful RemoteOK scrape
2. Successful YC scrape
3. Empty but valid scrape (trustworthy)
4. Scraper failure handling
5. Parser failure handling (found anchors but 0 jobs extracted)
6. HTTP/request failure handling
7. Playwright failure handling (timeout waiting for selector)
8. Suspicious / invalid result handling (empty scrape when active jobs exist)
9. Failed scrape does NOT increment missing state
10. Failed scrape does NOT expire jobs
11. Suspicious scrape does NOT trigger destructive lifecycle changes
12. Healthy scrape DOES update lifecycle correctly (seen reset, missing aged/expired)
13. Database failure rolls back appropriately
14. YC selector fallback behavior (location, description, and date attributes)
15. YC parser correctly extracts multiple jobs
16. Scrape run records success / failure correctly
17. Multi-user data isolation remains intact
18. Existing scoring behavior from Batch 1 remains intact
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.resume import Resume
from app.models.scrape_run import ScrapeRun
from app.models.user import User
from app.models.user_job import UserJob
from app.schemas.job import JobUpsertData
from app.scrapers.base import ScraperResult
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.yc_jobs import YCJobsScraper
from app.services.job_service import JobService
from app.services.scraper_service import ScraperService
from tests.conftest import FakeScraper, needs_db

pytestmark = needs_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_user(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"scraper-tester-{uuid.uuid4().hex[:6]}@example.com",
        name="Scraper Tester",
        password_hash="hash",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def existing_active_jobs(db: Session) -> list[Job]:
    """Create 2 active jobs for remoteok and 2 active jobs for yc_jobs."""
    now = datetime.now(UTC) - timedelta(hours=2)
    jobs = []
    for source in ["remoteok", "yc_jobs"]:
        for i in range(2):
            job = Job(
                id=uuid.uuid4(),
                title=f"{source} Active Job {i}",
                company="TechCorp",
                description="Python engineer position requiring FastAPI and Docker.",
                url=f"https://example.com/{source}/job-{uuid.uuid4().hex[:6]}",
                source=source,
                last_seen_at=now,
                missing_sync_count=0,
                expired_at=None,
                created_at=now,
                updated_at=now,
            )
            db.add(job)
            jobs.append(job)
    db.commit()
    for j in jobs:
        db.refresh(j)
    return jobs


# ---------------------------------------------------------------------------
# Test Suites
# ---------------------------------------------------------------------------

class TestRemoteOKScraper:

    def test_successful_remoteok_scrape(self) -> None:
        """1. Successful RemoteOK scrape with mock API response."""
        scraper = RemoteOKScraper()
        mock_data = [
            {"legal": "Notice here"},  # legal notice
            {
                "slug": "12345-backend-intern",
                "id": "12345",
                "position": "Backend Software Engineer Intern",
                "company": "Stripe",
                "description": "<p>We are seeking a Backend Intern with Python expertise to join our team.</p>",
                "url": "https://remoteok.com/remote-jobs/12345",
                "tags": ["python", "intern", "backend"],
                "date": "2026-10-01T00:00:00Z",
            },
            {
                "slug": "12346-senior-dev",
                "id": "12346",
                "position": "Senior Principal Architect",
                "company": "BigCorp",
                "description": "<p>15 years experience required for leadership role.</p>",
                "url": "https://remoteok.com/remote-jobs/12346",
                "tags": ["c++", "leadership"],
                "date": "2026-10-01T00:00:00Z",
            },
        ]

        with patch.object(scraper, "_fetch", return_value=mock_data):
            result = scraper.run()
            assert isinstance(result, ScraperResult)
            assert result.success is True
            assert len(result.jobs) == 1
            assert result.jobs[0].title == "Backend Software Engineer Intern"
            assert result.jobs[0].company == "Stripe"
            assert "Backend Intern with Python expertise" in result.jobs[0].description
            assert result.details["total_raw"] == 3
            assert result.details["skipped_keyword"] == 1

    def test_empty_but_valid_remoteok_scrape(self) -> None:
        """3. Empty but valid scrape (many raw jobs but 0 internship matches)."""
        scraper = RemoteOKScraper()
        mock_data = [
            {"legal": "Notice here"},
            {
                "slug": "999-senior-dev",
                "id": "999",
                "position": "Senior Architect",
                "company": "Corp",
                "description": "<p>20 years experience required.</p>",
                "url": "https://remoteok.com/remote-jobs/999",
                "tags": ["java"],
            },
        ]
        with patch.object(scraper, "_fetch", return_value=mock_data):
            result = scraper.run()
            assert isinstance(result, ScraperResult)
            assert result.success is True
            assert len(result.jobs) == 0
            assert result.is_suspicious is False  # raw records > 1, so legitimate 0 keyword matches

    def test_remoteok_http_request_failure(self) -> None:
        """6. HTTP/request failure handling."""
        scraper = RemoteOKScraper()
        request = httpx.Request("GET", "https://remoteok.com/api")
        with (
            patch("httpx.Client.get", return_value=httpx.Response(502, request=request)),
            pytest.raises(httpx.HTTPStatusError),
        ):
            scraper.run()


class TestYCScraper:

    def test_yc_selector_fallback_behavior(self) -> None:
        """14. YC selector fallback behavior for location, description, and date."""
        scraper = YCJobsScraper()

        # Mock card ElementHandle where first selector returns None and second returns element
        mock_card = MagicMock()

        def query_selector_side_effect(sel: str) -> MagicMock | None:
            if sel == "[class*='location']":
                return None  # First fails
            if sel == "[class*='remote']":
                el = MagicMock()
                el.inner_text.return_value = "San Francisco, CA (Remote)"
                return el
            if sel == "[class*='description']":
                return None  # First fails
            if sel == "[class*='snippet']":
                el = MagicMock()
                el.inner_text.return_value = "Building scalable cloud infrastructure with Kubernetes and Go."
                return el
            if sel == "time":
                return None
            if sel == "[data-created-at]":
                return None
            if sel == "[data-date]":
                el = MagicMock()
                el.get_attribute.side_effect = lambda a: "2026-09-15T12:00:00Z" if a == "data-date" else None
                return el
            return None

        mock_card.query_selector.side_effect = query_selector_side_effect

        loc = scraper._extract_location(mock_card)
        assert loc == "San Francisco, CA (Remote)"

        desc = scraper._extract_description(mock_card)
        assert desc == "Building scalable cloud infrastructure with Kubernetes and Go."

        posted = scraper._extract_posted_at(mock_card)
        assert posted is not None
        assert posted.year == 2026
        assert posted.month == 9

    def test_yc_parser_extracts_multiple_jobs(self) -> None:
        """15. YC parser correctly extracts multiple jobs without premature return."""
        scraper = YCJobsScraper()
        mock_page = MagicMock()

        # Two anchors
        anchor1 = MagicMock()
        anchor1.get_attribute.return_value = "/jobs/101"
        anchor1.inner_text.return_value = "Software Engineer Intern"

        anchor2 = MagicMock()
        anchor2.get_attribute.return_value = "/jobs/102"
        anchor2.inner_text.return_value = "Data Science Intern"

        mock_page.locator.return_value.all.return_value = [anchor1, anchor2]

        with patch.object(scraper, "_extract_from_anchor") as mock_extract:
            mock_extract.side_effect = [
                JobUpsertData(
                    title="Software Engineer Intern",
                    company="Company A",
                    description="Work on distributed systems and APIs with Python.",
                    url="https://www.workatastartup.com/jobs/101",
                    source="yc_jobs",
                ),
                JobUpsertData(
                    title="Data Science Intern",
                    company="Company B",
                    description="Train machine learning models with PyTorch and Pandas.",
                    url="https://www.workatastartup.com/jobs/102",
                    source="yc_jobs",
                ),
            ]
            jobs = scraper._extract_jobs(mock_page)
            assert len(jobs) == 2
            assert jobs[0].title == "Software Engineer Intern"
            assert jobs[1].title == "Data Science Intern"

    def test_yc_parser_failure_detected_when_anchors_exist(self) -> None:
        """5. Parser failure: found anchors but failed to parse any valid cards."""
        scraper = YCJobsScraper()
        mock_page = MagicMock()

        anchor = MagicMock()
        anchor.get_attribute.return_value = "/jobs/555"
        mock_page.locator.return_value.all.return_value = [anchor]

        # Card extractor fails or returns None for all anchors
        with patch.object(scraper, "_extract_from_anchor", return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                scraper._extract_jobs(mock_page)
            assert "parser failure" in str(exc_info.value).lower()


class TestScraperServiceLifecycleSafety:

    def test_healthy_scrape_updates_lifecycle_correctly(
        self, scraper_service: ScraperService, existing_active_jobs: list[Job], db: Session
    ) -> None:
        """12. Healthy scrape updates seen jobs and ages genuinely missing jobs."""
        source = "remoteok"
        active_remoteok = [j for j in existing_active_jobs if j.source == source]
        seen_job = active_remoteok[0]
        missing_job = active_remoteok[1]

        # Scraper returns seen_job and 1 new job
        fake_remoteok = FakeScraper(source)
        fake_remoteok.set_jobs([
            JobUpsertData(
                title=seen_job.title,
                company=seen_job.company,
                description=seen_job.description,
                url=seen_job.url,
                source=source,
            ),
            JobUpsertData(
                title="Brand New Job",
                company="NewCo",
                description="Brand new listing description.",
                url="https://example.com/remoteok/new-1",
                source=source,
            ),
        ])
        fake_yc = FakeScraper("yc_jobs")
        fake_yc.set_jobs([])

        with patch("app.scrapers.remoteok.RemoteOKScraper", return_value=fake_remoteok), \
             patch("app.scrapers.yc_jobs.YCJobsScraper", return_value=fake_yc):
            summary, _ = scraper_service.run_all()

        db.refresh(seen_job)
        db.refresh(missing_job)

        # seen_job had its last_seen_at updated and missing_sync_count is 0
        assert seen_job.missing_sync_count == 0
        assert seen_job.expired_at is None

        # missing_job was not in batch -> missing_sync_count incremented to 1
        assert missing_job.missing_sync_count == 1
        assert missing_job.expired_at is None

    def test_failed_scrape_does_not_increment_missing_or_expire_jobs(
        self, scraper_service: ScraperService, existing_active_jobs: list[Job], db: Session
    ) -> None:
        """4, 9, 10. Scraper failure records error and does NOT age or expire jobs."""
        source = "remoteok"
        active_remoteok = [j for j in existing_active_jobs if j.source == source]
        for j in active_remoteok:
            assert j.missing_sync_count == 0
            assert j.expired_at is None

        fake_remoteok = FakeScraper(source, raises=RuntimeError("RemoteOK connection reset"))
        fake_yc = FakeScraper("yc_jobs")
        fake_yc.set_jobs([])

        with patch("app.scrapers.remoteok.RemoteOKScraper", return_value=fake_remoteok), \
             patch("app.scrapers.yc_jobs.YCJobsScraper", return_value=fake_yc):
            summary, _ = scraper_service.run_all()

        run_ro = next(r for r in summary.runs if r.source == source)
        assert run_ro.error is not None
        assert "RemoteOK connection reset" in run_ro.error

        # Verify active jobs were NOT aged
        for j in active_remoteok:
            db.refresh(j)
            assert j.missing_sync_count == 0
            assert j.expired_at is None

    def test_suspicious_empty_scrape_does_not_trigger_mass_expiry(
        self, scraper_service: ScraperService, existing_active_jobs: list[Job], db: Session
    ) -> None:
        """8, 11. Suspicious empty scrape (0 jobs when active exist) skips lifecycle aging."""
        source = "yc_jobs"
        active_yc = [j for j in existing_active_jobs if j.source == source]
        assert len(active_yc) == 2

        # Fake scraper returns 0 jobs without throwing error
        fake_yc = FakeScraper(source)
        fake_yc.set_jobs([])
        fake_ro = FakeScraper("remoteok")
        fake_ro.set_jobs([])

        with patch("app.scrapers.remoteok.RemoteOKScraper", return_value=fake_ro), \
             patch("app.scrapers.yc_jobs.YCJobsScraper", return_value=fake_yc):
            summary, _ = scraper_service.run_all()

        yc_run = next(r for r in summary.runs if r.source == source)
        assert yc_run.error is not None
        assert "Suspicious empty scrape" in yc_run.error

        # None of the active YC jobs should have been aged
        for j in active_yc:
            db.refresh(j)
            assert j.missing_sync_count == 0
            assert j.expired_at is None

    def test_consecutive_missing_syncs_expire_job_only_on_healthy_scrapes(
        self, scraper_service: ScraperService, existing_active_jobs: list[Job], db: Session
    ) -> None:
        """12. Consecutive missing syncs on healthy scrapes mark job expired."""
        source = "remoteok"
        active_remoteok = [j for j in existing_active_jobs if j.source == source]
        target = active_remoteok[0]
        other = active_remoteok[1]

        # Sync 1: Healthy scrape that returns only 'other', not 'target'
        fake_ro_1 = FakeScraper(source)
        fake_ro_1.set_jobs([
            JobUpsertData(
                title=other.title,
                company=other.company,
                description=other.description,
                url=other.url,
                source=source,
            )
        ])
        fake_yc = FakeScraper("yc_jobs")
        fake_yc.set_jobs([])

        with patch("app.scrapers.remoteok.RemoteOKScraper", return_value=fake_ro_1), \
             patch("app.scrapers.yc_jobs.YCJobsScraper", return_value=fake_yc):
            scraper_service.run_all()

        db.refresh(target)
        assert target.missing_sync_count == 1
        assert target.expired_at is None

        # Sync 2: Again healthy scrape without 'target' -> should expire target
        fake_ro_2 = FakeScraper(source)
        fake_ro_2.set_jobs([
            JobUpsertData(
                title=other.title,
                company=other.company,
                description=other.description,
                url=other.url,
                source=source,
            )
        ])

        with patch("app.scrapers.remoteok.RemoteOKScraper", return_value=fake_ro_2), \
             patch("app.scrapers.yc_jobs.YCJobsScraper", return_value=fake_yc):
            scraper_service.run_all()

        db.refresh(target)
        assert target.missing_sync_count == 2
        assert target.expired_at is not None

    def test_database_failure_during_upsert_rolls_back(
        self, scraper_service: ScraperService, db: Session
    ) -> None:
        """13. Database failure during upsert rolls back cleanly."""
        job_service = JobService(db)
        jobs = [
            JobUpsertData(
                title="Rollback Test",
                company="FailCo",
                description="desc",
                url="https://example.com/rollback-1",
                source="remoteok",
            )
        ]

        with (
            patch.object(db, "commit", side_effect=RuntimeError("DB Disk Full")),
            pytest.raises(RuntimeError),
        ):
            job_service.upsert_jobs(jobs)

        # Confirm job was not committed
        row = db.scalar(select(Job).where(Job.url == "https://example.com/rollback-1"))
        assert row is None

    def test_scrape_run_records_counts_and_errors(
        self, scraper_service: ScraperService, db: Session
    ) -> None:
        """16. ScrapeRun records started_at, completed_at, jobs_found, jobs_new, error."""
        fake_ro = FakeScraper("remoteok")
        fake_ro.set_jobs([
            JobUpsertData(
                title="Job 1",
                company="Co",
                description="desc",
                url=f"https://example.com/run-record-{uuid.uuid4().hex}",
                source="remoteok",
            )
        ])
        fake_yc = FakeScraper("yc_jobs", raises=TimeoutError("Playwright timeout"))

        with patch("app.scrapers.remoteok.RemoteOKScraper", return_value=fake_ro), \
             patch("app.scrapers.yc_jobs.YCJobsScraper", return_value=fake_yc):
            summary, _ = scraper_service.run_all()

        runs = db.scalars(select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(2)).all()
        ro_run = next(r for r in runs if r.source == "remoteok")
        yc_run = next(r for r in runs if r.source == "yc_jobs")

        assert ro_run.jobs_found == 1
        assert ro_run.jobs_new == 1
        assert ro_run.error is None
        assert ro_run.completed_at is not None

        assert yc_run.jobs_found == 0
        assert yc_run.jobs_new == 0
        assert yc_run.error is not None
        assert "Playwright timeout" in yc_run.error
        assert yc_run.completed_at is not None


class TestScraperMultiUserIsolationAndScoring:

    def test_scraper_multi_user_isolation(
        self, db: Session, test_user: User, existing_active_jobs: list[Job]
    ) -> None:
        """17. Multi-user safety: scraping operations do not corrupt user_job records."""
        # Create a UserJob for test_user on an existing job
        job = existing_active_jobs[0]
        user_job = UserJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            job_id=job.id,
            status="applied",
            notes="Applied on company site.",
            match_score=88,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(user_job)
        db.commit()

        # Run scraper service
        service = ScraperService(db, user_id=test_user.id)
        fake_ro = FakeScraper("remoteok")
        fake_ro.set_jobs([
            JobUpsertData(
                title=job.title,
                company=job.company,
                description=job.description,
                url=job.url,
                source="remoteok",
            )
        ])
        fake_yc = FakeScraper("yc_jobs")
        fake_yc.set_jobs([])

        with patch("app.scrapers.remoteok.RemoteOKScraper", return_value=fake_ro), \
             patch("app.scrapers.yc_jobs.YCJobsScraper", return_value=fake_yc):
            service.run_all()

        # Verify test_user's UserJob was not mutated or overwritten
        db.refresh(user_job)
        assert user_job.status == "applied"
        assert user_job.notes == "Applied on company site."
        assert user_job.match_score == 88

    def test_batch_1_scoring_pipeline_integrity(
        self, db: Session, test_user: User, existing_active_jobs: list[Job]
    ) -> None:
        """18. Batch 1 regression check: auto-scoring pipeline functions with new scraper changes."""
        job = existing_active_jobs[0]
        resume = Resume(
            id=uuid.uuid4(),
            user_id=test_user.id,
            filename="resume.pdf",
            raw_text="Python FastAPI Docker",
            skills=["Python", "FastAPI", "Docker"],
            uploaded_at=datetime.now(UTC),
        )
        db.add(resume)
        db.commit()

        service = ScraperService(db, user_id=test_user.id)
        run = service.start_scoring_run(1, user_id=test_user.id)

        with patch("app.services.match_service.GeminiClient") as MockGemini:
            MockGemini.return_value.match_job.return_value = {
                "match_score": 92,
                "missing_skills": [],
                "match_summary": "Great match.",
            }
            service.run_auto_score([str(job.id)], scoring_run_id=run.id, user_id=test_user.id)

        db.refresh(run)
        assert run.status == "completed"
        assert run.scored_jobs == 1
        assert run.failed_jobs == 0

        uj = db.scalar(select(UserJob).where(UserJob.job_id == job.id, UserJob.user_id == test_user.id))
        assert uj is not None
        assert uj.match_score == 92
