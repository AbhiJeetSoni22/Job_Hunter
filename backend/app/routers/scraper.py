"""
Scraper router.

Handles HTTP for:
  POST /api/scraper/run     — trigger full sync from all sources
  GET  /api/scraper/status  — last run result per source

Runs synchronously. One "Sync Jobs" click → both scrapers run → response
returned with summary. No background workers, no task queue (ARCHITECTURE.md).
"""

from fastapi import APIRouter, status

from app.dependencies import DbSession
from app.schemas.job import ApiResponse, ScraperRunSummary, ScrapeRunResponse
from app.services.scraper_service import ScraperService

router = APIRouter(prefix="/scraper", tags=["scraper"])


# ── POST /api/scraper/run ──────────────────────────────────────────────────

@router.post(
    "/run",
    response_model=ApiResponse[ScraperRunSummary],
    status_code=status.HTTP_200_OK,
    summary="Run all scrapers",
    description=(
        "Trigger a full sync from all job sources (RemoteOK + YC Jobs). "
        "Runs synchronously. One source failing does not abort the other. "
        "Returns a per-source summary with jobs_found, jobs_new, and any error."
    ),
)
def run_scrapers(db: DbSession) -> ApiResponse[ScraperRunSummary]:
    summary = ScraperService(db).run_all()
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