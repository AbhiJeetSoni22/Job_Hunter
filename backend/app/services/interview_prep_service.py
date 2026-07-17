"""
interview_prep_service.py — AI Interview Preparation Generator (V1).

New, isolated feature. Does NOT modify:
    - job_service.py     (existing job read/update/delete logic)
    - match_service.py   (existing job-scoring logic)
    - resume_service.py  (upload / validation / deletion / storage)
    - resume_analysis_service.py (Resume Gap Analyzer)
    - Any existing router, schema, or model

Reuses existing infrastructure wherever safe, per the feature spec:
    - ResumeService.get_latest_with_text() — same resume-fetch path
      already used by match_service and resume_analysis_service,
      including its existing LookupError("No resume uploaded") when
      nothing is active.
    - db.get(Job, job_id) — same job-lookup pattern used by
      match_service._get_job() and job_service.get_job().
    - GeminiClient — new generate_interview_prep() method, added
      additively; existing methods are untouched.

Architecture rule (matches ARCHITECTURE.md):
    - No HTTP concerns here: no Request, no Response, no status codes.
    - Raise JobNotFoundError if job_id does not match any row.
    - Raise LookupError for "no active resume" (re-raised from
      ResumeService, not redefined here — single source of truth).
    - Stateless generation only — no database writes.
    - The router translates these into HTTP responses.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session  # type: ignore[import-not-found]

from app.ai.gemini_client import GeminiClient
from app.models.job import Job
from app.schemas.interview_prep import InterviewPrepResponse
from app.services.resume_service import ResumeService

logger = logging.getLogger(__name__)


class JobNotFoundError(Exception):
    """Raised when job_id does not match any row."""


class InterviewPrepService:
    """
    Orchestrates the AI Interview Preparation Generator: fetch the job,
    fetch the active resume, call Gemini, return structured prep material.

    Instantiated per request with an injected SQLAlchemy session:
        service = InterviewPrepService(db)
        result = service.generate(job_id)
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def generate(self, job_id: uuid.UUID) -> InterviewPrepResponse:
        """
        Run the AI Interview Preparation Generator for a given job.

        Args:
            job_id: UUID of the job to prepare for.

        Returns:
            InterviewPrepResponse with technical_questions,
            behavioral_questions, project_questions, topics_to_revise,
            and interview_tips.

        Raises:
            JobNotFoundError: if job_id does not match any row.
            LookupError:      if no active resume exists (upload one first).
            AIError:          if Gemini fails after all retry attempts.
        """
        job = self._get_job(job_id)

        # Reuses the exact same "active resume" lookup used by
        # resume_analysis_service and match_service — no duplicated
        # query logic, no new failure mode.
        resume = ResumeService(self._db).get_latest_with_text()

        logger.info(
            "InterviewPrepService.generate: job_id=%s resume_id=%s",
            job_id,
            resume.id,
        )

        client = GeminiClient()
        result = client.generate_interview_prep(
            resume_text=resume.raw_text,
            job_description=job.description,
            job_title=job.title,
            company_name=job.company,
        )

        logger.info(
            "InterviewPrepService.generate: completed job_id=%s "
            "project=%d technical=%d behavioral=%d topics=%d tips=%d",
            job_id,
            len(result["project_questions"]),
            len(result["technical_questions"]),
            len(result["behavioral_questions"]),
            len(result["topics_to_revise"]),
            len(result["interview_tips"]),
        )

        return InterviewPrepResponse(
            project_questions=result["project_questions"],
            technical_questions=result["technical_questions"],
            behavioral_questions=result["behavioral_questions"],
            topics_to_revise=result["topics_to_revise"],
            interview_tips=result["interview_tips"],
        )

    def _get_job(self, job_id: uuid.UUID) -> Job:
        job = self._db.get(Job, str(job_id))
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job
