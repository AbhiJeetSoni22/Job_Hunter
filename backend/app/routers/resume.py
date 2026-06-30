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

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

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


# ── POST /api/resume ───────────────────────────────────────────────────────
 
@router.post(
    "",
    response_model=ApiResponse[ResumeUploadResponse],
    status_code=status.HTTP_200_OK,
    summary="Upload resume PDF",
    description=(
        "Upload a PDF resume. Extracts text via PyMuPDF and skills via Gemini. "
        "Replaces any existing resume — only one active resume exists at a time."
    ),
)
async def upload_resume(
    db: DbSession,
    file: UploadFile = File(...),
) -> ApiResponse[ResumeUploadResponse]:
    try:
        result = await ResumeService(db).upload_resume(file)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_FILE", "message": str(exc)},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "EXTRACTION_ERROR", "message": str(exc)},
        ) from exc
 
    return ApiResponse(data=result)







# ── POST /api/resume ───────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ApiResponse[ResumeUploadResponse],
    status_code=status.HTTP_200_OK,
    summary="Upload resume PDF",
    description=(
        "Upload a PDF resume. Extracts text via PyMuPDF and skills via Gemini. "
        "Replaces any existing resume — only one active resume exists at a time."
    ),
)

 
 
# ── GET /api/resume ────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ApiResponse[ResumeResponse],
    summary="Get active resume",
)
def get_resume(db: DbSession) -> ApiResponse[ResumeResponse]:
    try:
        resume = ResumeService(db).get_latest()
    except LookupError as exc:
        raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "NO_RESUME", "message": str(exc)},
    ) from exc

    return ApiResponse(data=resume)
 
 
# ── DELETE /api/resume ─────────────────────────────────────────────────────

@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete active resume",
)
def delete_resume(db: DbSession) -> None:
    deleted = ResumeService(db).delete_latest()
    if not deleted:
        raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "NO_RESUME", "message": "No resume uploaded"},
)
 
# ── GET /api/resume/{resume_id} ────────────────────────────────────────────

@router.get(
    "/{resume_id}",
    response_model=ApiResponse[ResumeResponse],
    summary="Get resume by ID",
)
def get_resume_by_id(
    resume_id: uuid.UUID,
    db: DbSession,
) -> ApiResponse[ResumeResponse]:
    try:
        resume = ResumeService(db).get_by_id(resume_id)
    except LookupError as exc:
        raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "NOT_FOUND", "message": str(exc)},
    ) from exc

    return ApiResponse(data=resume)
