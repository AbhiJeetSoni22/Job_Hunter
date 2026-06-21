"""
Jobs router.

Handles all HTTP concerns for job endpoints:
  GET    /api/jobs              — paginated, filtered, sorted job list
  GET    /api/jobs/{id}         — single job detail
  POST   /api/jobs/{id}/score   — AI match scoring (Phase 2 stub)
  PATCH  /api/jobs/{id}         — update status / notes
  DELETE /api/jobs/{id}         — remove a job

Rules (ARCHITECTURE.md):
  - No database queries here — delegate everything to JobService.
  - No business logic here — validate input, call service, serialise output.
  - Translate service exceptions (LookupError, ValueError) to HTTP responses.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.dependencies import DbSession
from app.schemas.job import (
    ApiError,
    ApiResponse,
    JobResponse,
    JobUpdateRequest,
    JobUpdateResponse,
    PaginatedJobList,
    ScoreResult,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ── Error helpers ──────────────────────────────────────────────────────────

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


# ── GET /api/jobs ──────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ApiResponse[PaginatedJobList],
    summary="List jobs",
    description="Return a paginated, filtered, sorted list of jobs.",
)
def list_jobs(
    db: DbSession,
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    sort_by: str = Query(
        default="created_at",
        description="Sort column: created_at | posted_at | match_score",
    ),
    order: str = Query(default="desc", description="Sort direction: asc | desc"),
    status: str | None = Query(default=None, description="Filter by application status"),
    source: str | None = Query(default=None, description="Filter by source: remoteok | yc_jobs"),
    scored: bool | None = Query(default=None, description="True = scored only, False = unscored only"),
) -> ApiResponse[PaginatedJobList]:
    try:
        result = JobService(db).list_jobs(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order,
            status=status,
            source=source,
            scored=scored,
            # Phase 2: pass current_resume_uploaded_at from active resume
        )
    except ValueError as exc:
        raise _invalid_param(str(exc)) from exc

    return ApiResponse(data=result)


# ── GET /api/jobs/{id} ─────────────────────────────────────────────────────

@router.get(
    "/{job_id}",
    response_model=ApiResponse[JobResponse],
    summary="Get job detail",
    description="Return a single job including description, match analysis, and notes.",
)
def get_job(
    job_id: uuid.UUID,
    db: DbSession,
) -> ApiResponse[JobResponse]:
    try:
        job = JobService(db).get_job(
            job_id,
            # Phase 2: pass current_resume_uploaded_at
        )
    except LookupError:
        raise _not_found(job_id)

    return ApiResponse(data=job)


# ── POST /api/jobs/{id}/score ──────────────────────────────────────────────

@router.post(
    "/{job_id}/score",
    response_model=ApiResponse[ScoreResult],
    summary="Score job against resume",
    description=(
        "Run Gemini match analysis for a job against the current resume. "
        "Returns cached result if job was already scored. "
        "Phase 2: full Gemini integration. Phase 1B: stub response."
    ),
)
def score_job(
    job_id: uuid.UUID,
    db: DbSession,
) -> ApiResponse[ScoreResult]:
    # Verify job exists first
    try:
        JobService(db).get_job(job_id)
    except LookupError:
        raise _not_found(job_id)

    # Phase 2: delegate to match_service.score_job(job_id, db)
    # For now, return a clear stub so the endpoint is wired and testable.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Job scoring is implemented in Phase 2 (Gemini integration).",
        },
    )


# ── PATCH /api/jobs/{id} ───────────────────────────────────────────────────

@router.patch(
    "/{job_id}",
    response_model=ApiResponse[JobUpdateResponse],
    summary="Update job status or notes",
    description="Update application status and/or notes. Both fields are optional.",
)
def update_job(
    job_id: uuid.UUID,
    body: JobUpdateRequest,
    db: DbSession,
) -> ApiResponse[JobUpdateResponse]:
    try:
        result = JobService(db).update_job(job_id, body)
    except LookupError:
        raise _not_found(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_STATUS", "message": str(exc)},
        ) from exc

    return ApiResponse(data=result)


# ── DELETE /api/jobs/{id} ──────────────────────────────────────────────────

@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job",
    description="Permanently remove a job and its match data.",
)
def delete_job(
    job_id: uuid.UUID,
    db: DbSession,
) -> None:
    try:
        JobService(db).delete_job(job_id)
    except LookupError:
        raise _not_found(job_id)