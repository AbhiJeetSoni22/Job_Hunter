"""
Pydantic schemas for the AI Interview Preparation Generator.

New, isolated feature — does not modify or replace any schema used by
the existing job-scoring flow (see app/schemas/job.py) or the Resume
Gap Analyzer (see app/schemas/resume_analysis.py).

One shape:
    - InterviewPrepResponse : structured interview-prep result

No request schema is needed. POST /api/jobs/{job_id}/interview-prep takes
no body — the job (title, company, description) is resolved from the
path param and the resume from the currently active upload, the same
way POST /api/jobs/{job_id}/score works.
"""

from pydantic import BaseModel, ConfigDict, Field  # type: ignore[import-not-found]


class InterviewPrepResponse(BaseModel):
    """
    Structured interview preparation material from the AI Interview Prep
    Generator.

    Produced by GeminiClient.generate_interview_prep() via a dedicated
    prompt (INTERVIEW_PREP_PROMPT) — separate from the job-match scoring
    prompt and the Resume Gap Analyzer prompt.
    """

    model_config = ConfigDict(from_attributes=True)

    project_questions: list[str] = Field(
        default_factory=list,
        description=(
            "Highest-priority list. Questions about the candidate's own "
            "resume projects, tech choices, and experience — grounded "
            "directly in the resume text (up to 8)."
        ),
    )
    technical_questions: list[str] = Field(
        default_factory=list,
        description="Technical questions grounded in the job description's required technologies (up to 8).",
    )
    behavioral_questions: list[str] = Field(
        default_factory=list,
        description="Likely behavioral interview questions for this role (up to 6).",
    )
    topics_to_revise: list[str] = Field(
        default_factory=list,
        description="Concepts or topics the candidate should brush up on before the interview (up to 8).",
    )
    interview_tips: list[str] = Field(
        default_factory=list,
        description="Concrete, actionable tips for this specific interview (up to 6).",
    )
