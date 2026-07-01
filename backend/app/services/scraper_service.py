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

from app.ai.gemini_client import AIError
from app.models.scrape_run import ScrapeRun, SCRAPER_SOURCE_VALUES
from app.schemas.job import JobUpsertData, ScrapeRunResponse, ScraperRunSummary
from app.services import match_service
from app.services.job_service import JobService
from app.services.match_service import JobNotFoundError, NoResumeError

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

    def run_all(self) ->tuple[ScraperRunSummary, list[str]]:
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
        all_new_job_ids: list[str] = []

        for scraper in scrapers:
            result, new_ids = self._run_one(scraper)
            run_results.append(result)
            total_new += result.jobs_new
            all_new_job_ids.extend(new_ids)

        summary = ScraperRunSummary(
        runs=run_results,
        total_new=total_new,
        total_scored=0,  # scoring happens after response — see run_auto_score()
        )
        return summary, all_new_job_ids
    
    def run_auto_score(self, job_ids: list[str]) -> None:
        """
        Background-task entrypoint (Phase 5 — Feature 4).

        Must be called with a ScraperService built on its OWN fresh
        Session — the request-scoped session used for run_all() is
        closed as soon as the HTTP response is sent, before this runs.
        """
        scored = self._auto_score_new_jobs(job_ids)
        if scored:
            logger.info("background auto-score finished scored=%d", scored)

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

    def _run_one(self, scraper: "BaseScraper") -> tuple[ScrapeRunResponse, list[str]]:  # type: ignore[name-defined]
        """
        Execute a single scraper, upsert results, log the run.

        Catches all exceptions — a scraper crash is recorded in the
        ScrapeRun.error field and does not propagate upward.

        Returns the ScrapeRunResponse plus the list of newly inserted
        job ids (Phase 5 — Feature 4: auto-score new jobs).
        """
        source = scraper.source
        started_at = datetime.now(tz=timezone.utc)
        jobs_found = 0
        jobs_new = 0
        error: str | None = None
        new_job_ids: list[str] = []

        logger.info("Starting scraper: %s", source)

        try:
            raw_jobs: list[JobUpsertData] = scraper.run()
            jobs_found = len(raw_jobs)
            jobs_new = self._job_service.upsert_jobs(raw_jobs, new_job_ids=new_job_ids)
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

        return ScrapeRunResponse.model_validate(run), new_job_ids

    def _auto_score_new_jobs(self, job_ids: list[str]) -> int:
        """
        Score every newly inserted job against the active resume
        (Phase 5 — Feature 4).

        Only the jobs passed in are scored — pre-existing jobs are never
        touched. Reuses match_service.score_job(), so cache behaviour and
        Gemini retry logic are identical to manual scoring.

        Stops immediately (without erroring the whole sync) when no
        resume has been uploaded — auto-scoring is simply skipped.
        A per-job Gemini failure (AIError) is logged and does not abort
        scoring of the remaining new jobs.
        """
        if not job_ids:
            return 0

        scored = 0
        for job_id in job_ids:
            try:
                match_service.score_job(job_id, self._db)
                scored += 1
            except NoResumeError:
                logger.info("auto-score skipped — no active resume")
                break
            except JobNotFoundError:
                continue
            except AIError as exc:
                logger.warning(
                    "auto-score failed job_id=%s error=%s", job_id, exc
                )
                continue

        if scored:
            logger.info("auto-score complete scored=%d", scored)

        return scored

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