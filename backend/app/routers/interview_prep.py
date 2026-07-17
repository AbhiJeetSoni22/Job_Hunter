"""
Interview prep router — AI Interview Preparation Generator (new, isolated
feature).

Handles HTTP concerns for:
    POST /api/jobs/{job_id}/interview-prep — generate interview
    preparation material (technical questions, behavioral questions,
    resume/project questions, topics to revise, and interview tips)
    for the active resume against the given job.

Rules (ARCHITECTURE.md):
    - No business logic here.
    - No database access here.
    - Delegate everything to InterviewPrepService.
    - Translate service exceptions (JobNotFoundError, LookupError, AIError)
      to HTTP responses, matching the existing jobs.py / resume_analysis.py
      conventions.

This router does NOT modify app/routers/jobs.py. It is registered
separately in main.py, sharing the "/jobs" path prefix only for URL
readability — POST /jobs/{job_id}/interview-prep does not collide with
any existing route in the existing jobs router (different path).
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.ai.gemini_client import AIError
from app.dependencies import DbSession
from app.schemas.job import ApiResponse
from app.schemas.interview_prep import InterviewPrepResponse
from app.services.interview_prep_service import InterviewPrepService, JobNotFoundError

router = APIRouter(prefix="/jobs", tags=["interview-prep"])


# ── POST /api/jobs/{job_id}/interview-prep ─────────────────────────────────

@router.post(
    "/{job_id}/interview-prep",
    response_model=ApiResponse[InterviewPrepResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate AI interview preparation material for a job",
    description=(
        "Runs the AI Interview Preparation Generator against the given job "
        "and the currently active uploaded resume. Returns technical "
        "questions, behavioral questions, resume/project questions, topics "
        "to revise, and interview tips. Stateless — nothing is persisted. "
        "Does not affect existing job match scores or resume analysis."
    ),
)
def generate_interview_prep(
    job_id: uuid.UUID,
    db: DbSession,
) -> ApiResponse[InterviewPrepResponse]:
    try:
        result = InterviewPrepService(db).generate(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Job {job_id} not found"},
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "NO_RESUME",
                "message": "Upload a resume before generating interview prep.",
            },
        ) from exc
    except AIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "INTERVIEW_PREP_ERROR",
                "message": "Interview prep generation failed. Please try again.",
            },
        ) from exc

    return ApiResponse(data=result)
