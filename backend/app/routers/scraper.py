"""
Scraper router.

Handles HTTP for:
    POST /api/scraper/run     — trigger full sync from all sources
    GET  /api/scraper/status  — last run result per source

    Scraping + insertion is synchronous (fast). Auto-scoring of newly
    inserted jobs (Phase 5 — Feature 4) is scheduled as a FastAPI
    BackgroundTask so the response returns immediately after scraping —
    Gemini calls are too slow (10-30s/job) to block the HTTP response
    without tripping client/proxy timeouts. No task queue / worker process
    is introduced — this still runs in the same server process
    (ARCHITECTURE.md: no background workers, no task queue).
    """

from fastapi import APIRouter, status,BackgroundTasks

from app.database import SessionLocal
from app.dependencies import DbSession
from app.schemas.job import ApiResponse, ScraperRunSummary, ScrapeRunResponse
from app.services.scraper_service import ScraperService

router = APIRouter(prefix="/scraper", tags=["scraper"])


def _auto_score_in_background(job_ids: list[str]) -> None:
    """
    Runs after the HTTP response has already been sent.

    Uses a brand-new DB session — the request-scoped session is closed
    by the time this executes.
    """
    db = SessionLocal()
    try:
        ScraperService(db).run_auto_score(job_ids)
    finally:
        db.close()
# ── POST /api/scraper/run ──────────────────────────────────────────────────

@router.post(
    "/run",
    response_model=ApiResponse[ScraperRunSummary],
    status_code=status.HTTP_200_OK,
    summary="Run all scrapers",
    description=(
        "Trigger a full sync from all job sources (RemoteOK + YC Jobs). "
        "Scraping runs synchronously and the response returns as soon as "
        "it completes. One source failing does not abort the other. "
        "Newly inserted jobs are auto-scored in the background after the "
        "response is sent — total_scored in this response is always 0; "
        "poll GET /api/dashboard/stats or /api/scraper/status afterward "
        "to see updated scores."
    ),
)
def run_scrapers(db: DbSession, background_tasks: BackgroundTasks) -> ApiResponse[ScraperRunSummary]:
    summary, new_job_ids = ScraperService(db).run_all()
    if new_job_ids:
        background_tasks.add_task(_auto_score_in_background, new_job_ids)
    return ApiResponse(data=summary)

# ── GET /api/scraper/status ────────────────────────────────────────────────

@router.get(
    "/status",
    response_model=ApiResponse[list[ScrapeRunResponse]],
    summary="Scraper status",
    description=(
        "Return the most recent scrape run result for each configured source. "
        "Returns an empty list if no syncs have been run yet."
    ),
)
def scraper_status(db: DbSession) -> ApiResponse[list[ScrapeRunResponse]]:
    results = ScraperService(db).get_status()
    return ApiResponse(data=results)