"""
routers/jobs.py

HTTP layer for job endpoints.

Multi-user architecture:
  - Every endpoint requires authenticated CurrentUser.
  - JobService methods receive user.id to scope user-specific state (UserJob).
  - delete_job removes ONLY the user's UserJob relationship, leaving the global Job intact.
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.gemini_client import AIError
from app.config import get_settings
from app.dependencies import (
    CurrentUser,
    DbSession,
    check_ai_rate_limit,
    get_active_resume,
)
from app.models.resume import Resume
from app.schemas.job import (
    ApiResponse,
    BulkScoreResponse,
    JobResponse,
    JobUpdateRequest,
    JobUpdateResponse,
    PaginatedJobList,
    ScoreResponse,
)
from app.services import match_service
from app.services.job_service import JobService
from app.services.match_service import JobNotFoundError, NoResumeError
from app.services.scraper_service import ScraperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _not_found(job_id: uuid.UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "NOT_FOUND", "message": f"Job {job_id} not found"},
    )


def _invalid_param(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": "INVALID_PARAM", "message": message},
    )


def _get_resume_uploaded_at(db: Session, user_id: uuid.UUID) -> datetime | None:
    """
    Fetch the user's active resume's uploaded_at without raising.
    Returns None when no resume exists — read endpoints never block on this.
    """
    resume = (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    return resume.uploaded_at if resume else None


# ---------------------------------------------------------------------------
# GET /api/jobs
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=ApiResponse[PaginatedJobList],
    summary="List jobs",
    description="Return a paginated, filtered, sorted list of jobs for the authenticated user.",
)
def list_jobs(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    scored: bool | None = Query(default=None),
    include_expired: bool = Query(
        default=False,
        description="Include expired jobs in results. Defaults to False.",
    ),
) -> ApiResponse[PaginatedJobList]:
    current_resume_uploaded_at = _get_resume_uploaded_at(db, user.id)

    try:
        result = JobService(db).list_jobs(
            user.id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order,
            status=status,
            source=source,
            scored=scored,
            current_resume_uploaded_at=current_resume_uploaded_at,
            include_expired=include_expired,
        )
    except ValueError as exc:
        raise _invalid_param(str(exc)) from exc

    return ApiResponse(data=result)


# ---------------------------------------------------------------------------
# POST /api/jobs/bulk-score
# ---------------------------------------------------------------------------

@router.post(
    "/bulk-score",
    response_model=ApiResponse[BulkScoreResponse],
    summary="Bulk score unscored or stale jobs",
    description=(
        "Identify and score jobs that are currently unscored or have stale scores "
        "for the authenticated user. Schedules background scoring and returns a "
        "ScoringRun ID that can be polled via GET /api/scraper/scoring-status."
    ),
    dependencies=[Depends(check_ai_rate_limit)],
)
def bulk_score_jobs(
    user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
    include_stale: bool = Query(
        default=True,
        description="Include jobs with stale scores (scored against an older resume version)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        description="Maximum number of jobs to score in this batch",
    ),
    _resume: Resume = Depends(get_active_resume),
) -> ApiResponse[BulkScoreResponse]:
    max_limit = get_settings().MAX_BULK_SCORE_LIMIT
    if limit > max_limit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"limit cannot exceed {max_limit}",
            },
        )

    scraper_service = ScraperService(db, user_id=user.id)

    # Check for active concurrent scoring run for this user
    active_run = scraper_service.get_active_scoring_run(user.id)
    if active_run is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SCORING_IN_PROGRESS",
                "message": "A scoring run is already in progress for your account.",
                "scoring_run_id": str(active_run.id),
            },
        )

    job_service = JobService(db, user_id=user.id)
    eligible_job_ids = job_service.find_unscored_and_stale_job_ids(
        user_id=user.id,
        include_stale=include_stale,
        limit=limit,
    )

    if not eligible_job_ids:
        return ApiResponse(
            data=BulkScoreResponse(
                scoring_run_id=None,
                total_eligible=0,
                status="completed",
                message="All jobs are already scored and up-to-date.",
            )
        )

    job_id_strs = [str(jid) for jid in eligible_job_ids]
    scoring_run = scraper_service.start_scoring_run(
        total_jobs=len(job_id_strs),
        user_id=user.id,
    )

    from app.routers.scraper import _auto_score_in_background

    background_tasks.add_task(
        _auto_score_in_background,
        job_id_strs,
        scoring_run.id,
        user.id,
        True,  # force=True so stale jobs are refreshed
    )

    return ApiResponse(
        data=BulkScoreResponse(
            scoring_run_id=scoring_run.id,
            total_eligible=len(job_id_strs),
            status="running",
            message=f"Started scoring {len(job_id_strs)} jobs.",
        )
    )


# ---------------------------------------------------------------------------
# GET /api/jobs/{id}
# ---------------------------------------------------------------------------

@router.get(
    "/{job_id}",
    response_model=ApiResponse[JobResponse],
    summary="Get job detail",
)
def get_job(
    job_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[JobResponse]:
    current_resume_uploaded_at = _get_resume_uploaded_at(db, user.id)

    try:
        job = JobService(db).get_job(
            job_id,
            user_id=user.id,
            current_resume_uploaded_at=current_resume_uploaded_at,
        )
    except LookupError as exc:
        raise _not_found(job_id) from exc

    return ApiResponse(data=job)


# ---------------------------------------------------------------------------
# POST /api/jobs/{id}/score
# ---------------------------------------------------------------------------

@router.post(
    "/{job_id}/score",
    response_model=ApiResponse[ScoreResponse],
    summary="Score job against resume",
    dependencies=[Depends(check_ai_rate_limit)],
)
def score_job(
    job_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    force: bool = Query(
        default=False,
        description="Force recalculation and bypass cache",
    ),
    _resume: Resume = Depends(get_active_resume),  # 422 NO_RESUME if absent
) -> ApiResponse[ScoreResponse]:
    try:
        result = match_service.score_job(
            str(job_id),
            db,
            user_id=user.id,
            force=force,
        )
    except JobNotFoundError as exc:
        raise _not_found(job_id) from exc
    except NoResumeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "NO_RESUME",
                "message": "Upload a resume before scoring jobs",
            },
        ) from exc
    except (AIError, ValueError) as exc:
        logger.error("AI scoring failed for job %s: %s", job_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AI_ERROR", "message": "Failed to calculate job match score with AI."},
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error scoring job %s: %s", job_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SCORING_FAILED", "message": "An unexpected error occurred while scoring."},
        ) from exc

    return ApiResponse(data=ScoreResponse(**result), error=None)


# ---------------------------------------------------------------------------
# PATCH /api/jobs/{id}
# ---------------------------------------------------------------------------

@router.patch(
    "/{job_id}",
    response_model=ApiResponse[JobUpdateResponse],
    summary="Update job status or notes",
)
def update_job(
    job_id: uuid.UUID,
    body: JobUpdateRequest,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[JobUpdateResponse]:
    try:
        result = JobService(db).update_job(job_id, user_id=user.id, body=body)
    except LookupError as exc:
        raise _not_found(job_id) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_STATUS", "message": str(exc)},
        ) from exc

    return ApiResponse(data=result)


# ---------------------------------------------------------------------------
# DELETE /api/jobs/{id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user's tracking for a job",
)
def delete_job(
    job_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    try:
        JobService(db).delete_job(job_id, user_id=user.id)
    except LookupError as exc:
        raise _not_found(job_id) from exc