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

import uuid

from fastapi import APIRouter, HTTPException, Query, status, BackgroundTasks

from app.database import SessionLocal
from app.dependencies import DbSession
from app.schemas.job import (
    ApiResponse,
    ScoringStatusResponse,
    ScraperRunSummary,
    ScrapeRunResponse,
)
from app.services.scraper_service import ScraperService

router = APIRouter(prefix="/scraper", tags=["scraper"])


def _not_found(run_id: uuid.UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "NOT_FOUND", "message": f"Scoring run {run_id} not found"},
    )


def _auto_score_in_background(
    job_ids: list[str], scoring_run_id: uuid.UUID | None
) -> None:
    """
    Runs after the HTTP response has already been sent.

    Uses a brand-new DB session — the request-scoped session is closed
    by the time this executes.
    """
    db = SessionLocal()
    try:
        ScraperService(db).run_auto_score(job_ids, scoring_run_id=scoring_run_id)
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
        "response is sent — total_scored in this response is always 0. "
        "When new_job_ids is non-empty, scoring_run_id identifies the "
        "ScoringRun batch tracking that background work; poll "
        "GET /api/scraper/scoring-status?run_id=<id> to know when it "
        "reaches a terminal state, then refresh /api/dashboard/stats."
    ),
)
def run_scrapers(db: DbSession, background_tasks: BackgroundTasks) -> ApiResponse[ScraperRunSummary]:
    service = ScraperService(db)
    summary, new_job_ids = service.run_all()
    if new_job_ids:
        scoring_run = service.start_scoring_run(len(new_job_ids))
        summary.scoring_run_id = scoring_run.id
        background_tasks.add_task(
            _auto_score_in_background, new_job_ids, scoring_run.id
        )
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


# ── GET /api/scraper/scoring-status ─────────────────────────────────────────

@router.get(
    "/scoring-status",
    response_model=ApiResponse[ScoringStatusResponse],
    summary="Background auto-scoring progress",
    description=(
        "Report the persisted progress of one background auto-scoring "
        "batch (a ScoringRun), identified by the scoring_run_id returned "
        "from POST /api/scraper/run. status reaches 'completed' once "
        "every job in the batch has either been scored or permanently "
        "failed — this is a reliable terminal signal even when some "
        "Gemini calls fail, unlike checking match_score directly. There "
        "is no in-memory 'scoring in progress' flag; this is safe to "
        "call from any server process or after a restart."
    ),
)
def scoring_status(
    db: DbSession, run_id: uuid.UUID = Query(..., description="scoring_run_id from POST /api/scraper/run")
) -> ApiResponse[ScoringStatusResponse]:
    run = ScraperService(db).get_scoring_run(run_id)
    if run is None:
        raise _not_found(run_id)
    result = ScoringStatusResponse(
        status=run.status,
        total=run.total_jobs,
        scored=run.scored_jobs,
        failed=run.failed_jobs,
        pending=run.pending_jobs,
    )
    return ApiResponse(data=result)