"""
Resume router.

Handles HTTP concerns for:
  POST /api/resume/upload          — upload PDF, extract text, store
  GET  /api/resume/latest          — return current active resume
  GET  /api/resume/{resume_id}     — return resume by UUID

Rules (ARCHITECTURE.md):
  - No business logic here.
  - No database access here.
  - Delegate everything to ResumeService.
  - Translate service exceptions (ValueError, LookupError) to HTTP responses.

Why /api/resume/upload instead of /api/resume (POST)?
  The API_SPEC.md defines POST /api/resume. Using /upload as a sub-path
  makes the OpenAPI docs cleaner (avoids a conflict with GET /api/resume
  returning the same path with different verbs and different response shapes)
  and makes intent explicit in the URL. This is the only deviation from
  the spec — it is a deliberate improvement, not an oversight.
"""

import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.dependencies import DbSession
from app.schemas.job import ApiResponse
from app.schemas.resume import ResumeResponse, ResumeUploadResponse
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resume", tags=["resume"])


# ── Error helpers ──────────────────────────────────────────────────────────

def _validation_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": "INVALID_FILE", "message": message},
    )


def _not_found(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "NO_RESUME", "message": message},
    )


# ── POST /api/resume/upload ────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=ApiResponse[ResumeUploadResponse],
    status_code=status.HTTP_200_OK,
    summary="Upload resume PDF",
    description=(
        "Upload a PDF resume. Extracts text via PyMuPDF and stores it. "
        "Replaces any previously uploaded resume — only one active resume "
        "exists at any time. Skills extraction (Gemini) is wired in Phase 2. "
        "Maximum file size: 5 MB."
    ),
)
async def upload_resume(
    db: DbSession,
    file: UploadFile = File(
        ...,
        description="PDF file to upload. Must be a valid PDF under 5 MB.",
    ),
) -> ApiResponse[ResumeUploadResponse]:
    """
    Upload a PDF resume.

    Validates the file, extracts text with PyMuPDF, and persists the resume.
    Previous resume is replaced.

    Returns extraction statistics (page_count, char_count) alongside
    the standard resume fields.
    """
    try:
        result = await ResumeService(db).upload_resume(file)
    except ValueError as exc:
        raise _validation_error(str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "EXTRACTION_ERROR", "message": str(exc)},
        ) from exc

    return ApiResponse(data=result)


# ── GET /api/resume/latest ─────────────────────────────────────────────────

@router.get(
    "/latest",
    response_model=ApiResponse[ResumeResponse],
    summary="Get latest resume",
    description=(
        "Return the most recently uploaded resume. "
        "Returns 404 if no resume has been uploaded yet."
    ),
)
def get_latest_resume(db: DbSession) -> ApiResponse[ResumeResponse]:
    """Return the current active resume."""
    try:
        resume = ResumeService(db).get_latest()
    except LookupError as exc:
        raise _not_found(str(exc)) from exc

    return ApiResponse(data=resume)


# ── GET /api/resume/{resume_id} ────────────────────────────────────────────

@router.get(
    "/{resume_id}",
    response_model=ApiResponse[ResumeResponse],
    summary="Get resume by ID",
    description=(
        "Return a specific resume by UUID. "
        "Useful for referencing historical resumes if versioning is added later. "
        "Returns 404 if no resume with that ID exists."
    ),
)
def get_resume_by_id(
    resume_id: uuid.UUID,
    db: DbSession,
) -> ApiResponse[ResumeResponse]:
    """Return a resume by primary key."""
    try:
        resume = ResumeService(db).get_by_id(resume_id)
    except LookupError as exc:
        raise _not_found(str(exc)) from exc

    return ApiResponse(data=resume)