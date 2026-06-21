"""
Scraper service.

Orchestrates all scraper sources, persists scrape run logs, and delegates
job storage to JobService. Contains no HTTP concerns.

Architecture rules (ARCHITECTURE.md):
  - scraper_service calls job_service — never the reverse.
  - scrapers never import from services.
  - One ScrapeRun row is written per source per sync, regardless of success.

Phase 1B: actual scraper implementations (RemoteOKScraper, YCJobsScraper)
are not yet built. ScraperService expects any object implementing BaseScraper.
The run_all() method works with the placeholder stubs in scrapers/.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.scrape_run import ScrapeRun, SCRAPER_SOURCE_VALUES
from app.schemas.job import JobUpsertData, ScrapeRunResponse, ScraperRunSummary
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


class ScraperService:
    """
    Orchestrates job collection from all configured sources.

    Usage:
        service = ScraperService(db)
        summary = service.run_all()
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._job_service = JobService(db)

    # ── Public API ─────────────────────────────────────────────────────────

    def run_all(self) -> ScraperRunSummary:
        """
        Run every configured scraper source sequentially.

        One source failing does NOT abort subsequent sources. Each run is
        logged individually. Returns a summary of all runs.

        Returns:
            ScraperRunSummary with one ScrapeRunResponse per source
            and a total_new count across all sources.
        """
        # Import here to avoid circular import at module load time.
        # Scrapers are instantiated fresh per run — no shared state.
        from app.scrapers.remoteok import RemoteOKScraper
        from app.scrapers.yc_jobs import YCJobsScraper

        scrapers = [
            RemoteOKScraper(),
            YCJobsScraper(),
        ]

        run_results: list[ScrapeRunResponse] = []
        total_new = 0

        for scraper in scrapers:
            result = self._run_one(scraper)
            run_results.append(result)
            total_new += result.jobs_new

        return ScraperRunSummary(runs=run_results, total_new=total_new)

    def get_status(self) -> list[ScrapeRunResponse]:
        """
        Return the most recent scrape run for each known source.

        Used by GET /api/scraper/status. Returns one entry per source,
        even if a source has never been run (returns None for that source
        by omitting it — the router handles the empty case).
        """
        results: list[ScrapeRunResponse] = []

        for source in SCRAPER_SOURCE_VALUES:
            run = self._latest_run_for_source(source)
            if run is not None:
                results.append(ScrapeRunResponse.model_validate(run))

        return results

    # ── Private helpers ────────────────────────────────────────────────────

    def _run_one(self, scraper: "BaseScraper") -> ScrapeRunResponse:  # type: ignore[name-defined]
        """
        Execute a single scraper, upsert results, log the run.

        Catches all exceptions — a scraper crash is recorded in the
        ScrapeRun.error field and does not propagate upward.
        """
        source = scraper.source
        started_at = datetime.now(tz=timezone.utc)
        jobs_found = 0
        jobs_new = 0
        error: str | None = None

        logger.info("Starting scraper: %s", source)

        try:
            raw_jobs: list[JobUpsertData] = scraper.run()
            jobs_found = len(raw_jobs)
            jobs_new = self._job_service.upsert_jobs(raw_jobs)
            logger.info(
                "Scraper %s complete: found=%d new=%d",
                source, jobs_found, jobs_new,
            )
        except Exception as exc:
            error = str(exc)
            logger.error("Scraper %s failed: %s", source, error, exc_info=True)

        completed_at = datetime.now(tz=timezone.utc)

        run = self._persist_run(
            source=source,
            jobs_found=jobs_found,
            jobs_new=jobs_new,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
        )

        return ScrapeRunResponse.model_validate(run)

    def _persist_run(
        self,
        *,
        source: str,
        jobs_found: int,
        jobs_new: int,
        error: str | None,
        started_at: datetime,
        completed_at: datetime,
    ) -> ScrapeRun:
        """Insert a ScrapeRun row and return it."""
        run = ScrapeRun(
            source=source,
            jobs_found=jobs_found,
            jobs_new=jobs_new,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
        )
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)
        return run

    def _latest_run_for_source(self, source: str) -> ScrapeRun | None:
        """Return the most recent ScrapeRun for a given source, or None."""
        from sqlalchemy import select

        stmt = (
            select(ScrapeRun)
            .where(ScrapeRun.source == source)
            .order_by(ScrapeRun.started_at.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()


# ---------------------------------------------------------------------------
# BaseScraper interface — referenced by ScraperService._run_one()
# Actual implementations live in app/scrapers/
# ---------------------------------------------------------------------------

from app.scrapers.base import BaseScraper  # noqa: E402 — import after class def