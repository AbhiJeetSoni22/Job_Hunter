"""
routers/jobs.py

HTTP layer for job endpoints.

Multi-user architecture:
  - Every endpoint requires authenticated CurrentUser.
  - JobService methods receive user.id to scope user-specific state (UserJob).
  - delete_job removes ONLY the user's UserJob relationship, leaving the global Job intact.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import CurrentUser, DbSession, get_active_resume
from app.models.resume import Resume
from app.schemas.job import (
    ApiError,
    ApiResponse,
    JobResponse,
    JobUpdateRequest,
    JobUpdateResponse,
    PaginatedJobList,
    ScoreResponse,
)
from app.services import match_service
from app.services.job_service import JobService
from app.services.match_service import JobNotFoundError, NoResumeError
from app.ai.gemini_client import AIError

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
    except LookupError:
        raise _not_found(job_id)

    return ApiResponse(data=job)


# ---------------------------------------------------------------------------
# POST /api/jobs/{id}/score
# ---------------------------------------------------------------------------

@router.post(
    "/{job_id}/score",
    response_model=ApiResponse[ScoreResponse],
    summary="Score job against resume",
)
def score_job(
    job_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    _resume: Resume = Depends(get_active_resume),  # 422 NO_RESUME if absent
) -> ApiResponse[ScoreResponse]:
    try:
        result = match_service.score_job(str(job_id), db, user_id=user.id)
    except JobNotFoundError:
        raise _not_found(job_id)
    except NoResumeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "NO_RESUME",
                "message": "Upload a resume before scoring jobs",
            },
        )
    except AIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AI_ERROR", "message": str(exc)},
        )

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
    except LookupError:
        raise _not_found(job_id)
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
    except LookupError:
        raise _not_found(job_id)