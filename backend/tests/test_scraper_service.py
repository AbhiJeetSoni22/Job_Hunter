"""
test_scraper_service.py

Tests for app.services.scraper_service.ScraperService.

Patch strategy:
  run_all() does local imports:
      from app.scrapers.remoteok import RemoteOKScraper
      from app.scrapers.yc_jobs import YCJobsScraper
  Correct patch targets:
      app.scrapers.remoteok.RemoteOKScraper
      app.scrapers.yc_jobs.YCJobsScraper
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import needs_db, FakeScraper

pytestmark = needs_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_scrapers(remoteok_instance, yc_instance):
    """
    Patch the two scraper classes at their definition modules.
    run_all() does local imports, so we must patch the source modules,
    not app.services.scraper_service.
    """
    return patch.multiple(
        "app.scrapers.remoteok",
        RemoteOKScraper=MagicMock(return_value=remoteok_instance),
    ), patch.multiple(
        "app.scrapers.yc_jobs",
        YCJobsScraper=MagicMock(return_value=yc_instance),
    )


def _run_with_fakes(scraper_service, remoteok: FakeScraper, yc: FakeScraper):
    """Run run_all() with both scrapers patched."""
    p1 = patch("app.scrapers.remoteok.RemoteOKScraper", return_value=remoteok)
    p2 = patch("app.scrapers.yc_jobs.YCJobsScraper", return_value=yc)
    with p1, p2:
        return scraper_service.run_all()


def _empty_scrapers():
    remoteok = FakeScraper("remoteok")
    remoteok.set_jobs([])
    yc = FakeScraper("yc_jobs")
    yc.set_jobs([])
    return remoteok, yc


# ---------------------------------------------------------------------------
# run_all — happy path
# ---------------------------------------------------------------------------

class TestRunAll:

    def test_run_all_returns_scraper_run_summary(self, scraper_service):
        from app.schemas.job import ScraperRunSummary

        remoteok, yc = _empty_scrapers()
        result = _run_with_fakes(scraper_service, remoteok, yc)

        assert isinstance(result, ScraperRunSummary)
        assert len(result.runs) == 2

    def test_run_all_total_new_is_sum(self, scraper_service):
        from app.schemas.job import JobUpsertData

        remoteok = FakeScraper("remoteok")
        remoteok.set_jobs([
            JobUpsertData(
                title="Job A", company="Co", description="desc",
                url="https://scraper-test.example.com/run/1",
                source="remoteok",
            ),
        ])
        yc = FakeScraper("yc_jobs")
        yc.set_jobs([
            JobUpsertData(
                title="Job B", company="Co", description="desc",
                url="https://scraper-test.example.com/run/2",
                source="yc_jobs",
            ),
        ])

        result = _run_with_fakes(scraper_service, remoteok, yc)
        assert result.total_new == 2

    def test_run_all_persists_scrape_run_rows(self, scraper_service, db):
        from app.models.scrape_run import ScrapeRun
        from sqlalchemy import select

        remoteok, yc = _empty_scrapers()
        _run_with_fakes(scraper_service, remoteok, yc)

        rows = db.scalars(select(ScrapeRun)).all()
        sources = {r.source for r in rows}
        assert "remoteok" in sources
        assert "yc_jobs" in sources


# ---------------------------------------------------------------------------
# run_all — scraper failure handling
# ---------------------------------------------------------------------------

class TestRunAllFailure:

    def test_failing_scraper_records_error(self, scraper_service):
        remoteok = FakeScraper("remoteok", raises=RuntimeError("network timeout"))
        yc, _ = _empty_scrapers()[1], None
        yc = FakeScraper("yc_jobs")
        yc.set_jobs([])

        result = _run_with_fakes(scraper_service, remoteok, yc)

        remoteok_run = next(r for r in result.runs if r.source == "remoteok")
        assert remoteok_run.error is not None
        assert "network timeout" in remoteok_run.error

    def test_one_failure_does_not_abort_other_scraper(self, scraper_service):
        remoteok = FakeScraper("remoteok", raises=RuntimeError("boom"))
        yc = FakeScraper("yc_jobs")
        yc.set_jobs([])

        result = _run_with_fakes(scraper_service, remoteok, yc)

        assert len(result.runs) == 2
        yc_run = next(r for r in result.runs if r.source == "yc_jobs")
        assert yc_run.error is None

    def test_failed_run_has_completed_at_set(self, scraper_service):
        remoteok = FakeScraper("remoteok", raises=Exception("fail"))
        yc = FakeScraper("yc_jobs")
        yc.set_jobs([])

        result = _run_with_fakes(scraper_service, remoteok, yc)

        remoteok_run = next(r for r in result.runs if r.source == "remoteok")
        assert remoteok_run.completed_at is not None

    def test_both_fail_total_new_zero(self, scraper_service):
        remoteok = FakeScraper("remoteok", raises=Exception("err1"))
        yc = FakeScraper("yc_jobs", raises=Exception("err2"))

        result = _run_with_fakes(scraper_service, remoteok, yc)
        assert result.total_new == 0


# ---------------------------------------------------------------------------
# ScrapeRunResponse shape
# ---------------------------------------------------------------------------

class TestScrapeRunResponseShape:

    def test_run_response_has_expected_fields(self, scraper_service):
        from app.schemas.job import ScrapeRunResponse

        remoteok, yc = _empty_scrapers()
        result = _run_with_fakes(scraper_service, remoteok, yc)

        for run in result.runs:
            assert isinstance(run, ScrapeRunResponse)
            assert run.source in ("remoteok", "yc_jobs")
            assert isinstance(run.jobs_found, int)
            assert isinstance(run.jobs_new, int)
            assert run.started_at is not None


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

class TestGetStatus:

    def test_returns_empty_list_when_no_runs(self, scraper_service):
        result = scraper_service.get_status()
        assert isinstance(result, list)
        assert result == []

    def test_returns_latest_run_per_source(self, scraper_service):
        from app.schemas.job import ScrapeRunResponse

        remoteok, yc = _empty_scrapers()
        _run_with_fakes(scraper_service, remoteok, yc)

        status = scraper_service.get_status()
        assert len(status) == 2
        sources = {r.source for r in status}
        assert sources == {"remoteok", "yc_jobs"}

    def test_get_status_returns_scrape_run_response_list(self, scraper_service):
        from app.schemas.job import ScrapeRunResponse

        remoteok, yc = _empty_scrapers()
        _run_with_fakes(scraper_service, remoteok, yc)

        status = scraper_service.get_status()
        for item in status:
            assert isinstance(item, ScrapeRunResponse)

    def test_get_status_shows_only_latest_run(self, scraper_service):
        # Run twice; get_status should return one row per source
        for _ in range(2):
            remoteok, yc = _empty_scrapers()
            _run_with_fakes(scraper_service, remoteok, yc)

        status = scraper_service.get_status()
        assert len(status) == 2