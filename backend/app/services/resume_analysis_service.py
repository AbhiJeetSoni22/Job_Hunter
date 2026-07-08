"""
resume_analysis_service.py — Resume Gap Analyzer (Phase 1, backend only).

New, isolated feature. Does NOT modify:
    - resume_service.py       (upload / validation / deletion / storage)
    - match_service.py        (existing job-scoring logic)
    - Any existing router, schema, or model

    Reuses existing infrastructure wherever safe, per the feature spec:
        - ResumeService.get_latest_with_text() — same resume-fetch path
        already used by match_service, including its existing
        LookupError("No resume uploaded") when nothing is active.
        - GeminiClient — new analyze_resume_gap() method, added additively;
        extract_skills() and match_job() are untouched.

        Architecture rule (matches ARCHITECTURE.md):
            - No HTTP concerns here: no Request, no Response, no status codes.
            - Raise ValueError for validation failures.
            - Raise LookupError for "no active resume" (re-raised from
            ResumeService, not redefined here — single source of truth).
            - The router translates these into HTTP responses.
            """

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.ai.gemini_client import GeminiClient
from app.schemas.resume_analysis import ResumeAnalysisResponse
from app.services.resume_service import ResumeService

logger = logging.getLogger(__name__)

# Soft cap on job description length. Long real-world postings are common
# (see "Long JD" test case) — rather than rejecting them, truncate to keep
# Gemini cost/latency bounded. This does not affect resume text handling,
# which already has no such cap elsewhere in the codebase.
MAX_JOB_DESCRIPTION_LENGTH: int = 20_000


class ResumeAnalysisService:
    """
    Orchestrates the Resume Gap Analyzer: fetch active resume, validate
    the job description, call Gemini, return structured feedback.

    Instantiated per request with an injected SQLAlchemy session:
        service = ResumeAnalysisService(db)
        result = service.analyze(job_description)
        """

    def __init__(self, db: Session) -> None:
        self._db = db

    def analyze(self, job_description: str) -> ResumeAnalysisResponse:
        """
        Run the Resume Gap Analyzer against the active resume.

        Args:
            job_description: Raw job description text from the request body.

            Returns:
                ResumeAnalysisResponse with match_score, summary, missing_skills,
                strengths, suggestions, and ats_tips.

                Raises:
        ValueError:  if job_description is empty.
        LookupError: if no active resume exists (upload one first).
        AIError:     if Gemini fails after all retry attempts.
        """
        jd = self._validate_job_description(job_description)

        # Reuses the exact same "active resume" lookup used by resume reads
        # and match_service — no duplicated query logic, no new failure mode.
        resume = ResumeService(self._db).get_latest_with_text()

        logger.info(
            "ResumeAnalysisService.analyze: resume_id=%s desc_len=%d",
            resume.id,
            len(jd),
        )

        client = GeminiClient()
        result = client.analyze_resume_gap(resume.raw_text, jd)

        logger.info(
            "ResumeAnalysisService.analyze: completed resume_id=%s score=%d",
            resume.id,
            result["match_score"],
        )

        return ResumeAnalysisResponse(
    match_score=result["match_score"],
    summary=result["summary"],
    missing_skills=result["missing_skills"],
    strengths=result["strengths"],
    suggestions=result["suggestions"],
    ats_tips=result["ats_tips"],
)

    @staticmethod
    def _validate_job_description(job_description: str) -> str:
        """
        Validate and normalise the job description.

        Raises:
            ValueError: if empty or whitespace-only.
            """
        if not job_description or not job_description.strip():
            raise ValueError("job_description must not be empty")

        jd = job_description.strip()

        if len(jd) > MAX_JOB_DESCRIPTION_LENGTH:
            logger.warning(
                "ResumeAnalysisService: job_description truncated from %d to %d chars",
                len(jd),
                MAX_JOB_DESCRIPTION_LENGTH,
            )
            jd = jd[:MAX_JOB_DESCRIPTION_LENGTH]

        return jd