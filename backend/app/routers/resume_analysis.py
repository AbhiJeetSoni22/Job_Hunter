"""
Resume analysis router — Resume Gap Analyzer (new, isolated feature).

Handles HTTP concerns for:
    POST /api/resume/analyze — analyze the active resume against a pasted
    job description and return structured
    improvement feedback.

    Rules (ARCHITECTURE.md):
        - No business logic here.
        - No database access here.
        - Delegate everything to ResumeAnalysisService.
        - Translate service exceptions (ValueError, LookupError, AIError) to
        HTTP responses, matching the existing resume.py / jobs.py conventions.

        This router does NOT modify app/routers/resume.py. It is registered
        separately in main.py, sharing the "/resume" path prefix only for URL
        readability — POST /resume/analyze does not collide with any existing
        route (different path and, where paths could overlap, different HTTP
        method) in the existing resume or jobs routers.
        """

from fastapi import APIRouter, status, HTTPException

from app.ai.gemini_client import AIError
from app.dependencies import DbSession
from app.schemas.job import ApiResponse
from app.schemas.resume_analysis import ResumeAnalysisRequest, ResumeAnalysisResponse
from app.services.resume_analysis_service import ResumeAnalysisService

router = APIRouter(prefix="/resume", tags=["resume-analysis"])


# ── POST /api/resume/analyze ────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=ApiResponse[ResumeAnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Analyze the active resume against a job description",
    description=(
        "Runs the Resume Gap Analyzer against the currently active uploaded "
        "resume and a supplied job description. Returns a match score, "
        "summary, missing skills, existing strengths, resume improvement "
        "suggestions, and ATS optimization tips. Does not upload a new "
        "resume and does not affect existing job match scores."
    ),
)
def analyze_resume(
    payload: ResumeAnalysisRequest,
    db: DbSession,
) -> ApiResponse[ResumeAnalysisResponse]:
    try:
        result = ResumeAnalysisService(db).analyze(payload.job_description)
    except LookupError as exc:
        raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail={
        "code": "NO_RESUME",
        "message": "Upload a resume before running analysis.",
    },
   ) from exc
    except ValueError as exc:
        raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail={"code": "EMPTY_JOB_DESCRIPTION", "message": str(exc)},
    ) from exc
    except AIError as exc:
        raise HTTPException(
    status_code=status.HTTP_502_BAD_GATEWAY,
    detail={
        "code": "ANALYSIS_ERROR",
        "message": "Resume analysis failed. Please try again.",
    },
    ) from exc

    return ApiResponse(data=result)