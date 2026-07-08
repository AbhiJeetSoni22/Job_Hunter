"""
Pydantic schemas for the Resume Gap Analyzer feature.

New, isolated feature — does not modify or replace any schema used by
the existing resume upload/read/delete flow (see app/schemas/resume.py)
or the existing job-scoring flow (see app/schemas/job.py).

Two shapes:
    - ResumeAnalysisRequest  : request body for POST /api/resume/analyze
    - ResumeAnalysisResponse : structured gap-analysis result
    """

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ResumeAnalysisRequest(BaseModel):
    """
    Request body for POST /api/resume/analyze.

    The resume itself is NOT part of the request — it is always read from
    the currently active uploaded resume (see ResumeService.get_latest_with_text).
    """

    job_description: str = Field(
        ...,
        min_length=1,
        description="Full plain text of the job description to analyze against the active resume.",
    )


    # ---------------------------------------------------------------------------
    # Response
    # ---------------------------------------------------------------------------

class ResumeAnalysisResponse(BaseModel):
    """
    Structured feedback from the Resume Gap Analyzer.

    Produced by GeminiClient.analyze_resume_gap() via a dedicated prompt
    (RESUME_GAP_ANALYSIS_PROMPT) — separate from the existing job-match
    scoring prompt and pipeline.
    """

    model_config = ConfigDict(from_attributes=True)

    match_score: int = Field(
        ..., ge=0, le=100, description="Technical fit score for this resume against this job description, 0-100."
    )
    summary: str = Field(..., description="One to two sentence overview of the candidate's fit for this role.")
    missing_skills: list[str] = Field(
        default_factory=list,
        description="Skills required by the job description but not found in the resume (up to 5).",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Skills or experience in the resume that directly match the job description (up to 5).",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Concrete, actionable resume improvements for this specific role (up to 5).",
    )
    ats_tips: list[str] = Field(
        default_factory=list,
        description="Applicant Tracking System optimization tips for this job description (up to 5).",
    )