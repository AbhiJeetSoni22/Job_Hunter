"""
Scraper router.

Handles HTTP for:
    POST /api/scraper/run     — trigger full sync from all sources
    GET  /api/scraper/status  — last run result per source
    GET  /api/scraper/scoring-status — background auto-scoring progress

Multi-user architecture:
    - Scrapers scrape global jobs deduplicated by canonical URL.
    - Background auto-scoring is scoped to the CurrentUser who initiated the sync.
    - ScoringRun belongs to user.id and scores against user's active resume.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, status, BackgroundTasks

from app.database import SessionLocal
from app.dependencies import CurrentUser, DbSession
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
    job_ids: list[str],
    scoring_run_id: uuid.UUID | None,
    user_id: uuid.UUID,
) -> None:
    """
    Runs after the HTTP response has already been sent.

    Uses a brand-new DB session — the request-scoped session is closed
    by the time this executes.
    """
    db = SessionLocal()
    try:
        ScraperService(db).run_auto_score(
            job_ids,
            scoring_run_id=scoring_run_id,
            user_id=user_id,
        )
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
        "Newly inserted jobs are auto-scored in the background for the authenticated user."
    ),
)
def run_scrapers(
    user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ApiResponse[ScraperRunSummary]:
    service = ScraperService(db)
    summary, new_job_ids = service.run_all()
    if new_job_ids:
        scoring_run = service.start_scoring_run(len(new_job_ids), user_id=user.id)
        summary.scoring_run_id = scoring_run.id
        background_tasks.add_task(
            _auto_score_in_background,
            new_job_ids,
            scoring_run.id,
            user.id,
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
def scraper_status(
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[list[ScrapeRunResponse]]:
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
        "from POST /api/scraper/run. Scoped to the authenticated user."
    ),
)
def scoring_status(
    user: CurrentUser,
    db: DbSession,
    run_id: uuid.UUID = Query(..., description="scoring_run_id from POST /api/scraper/run"),
) -> ApiResponse[ScoringStatusResponse]:
    run = ScraperService(db).get_scoring_run(run_id, user_id=user.id)
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