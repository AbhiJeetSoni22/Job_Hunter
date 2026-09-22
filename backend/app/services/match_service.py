"""
match_service.py — Phase 2C & Multi-User Data Isolation
Responsibility: AI job match scoring with resume-keyed cache scoped per user.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gemini_client import GeminiClient, AIError
from app.models.job import Job
from app.models.resume import Resume
from app.models.user_job import UserJob

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Recommendation labels (Phase 5 — Feature 5)
# ---------------------------------------------------------------------------

def recommendation_label(score: int | None) -> str | None:
    """
    Map a match score to a human-readable recommendation label.

    95-100  -> "Excellent Match"
    80-94   -> "Strong Match"
    65-79   -> "Potential Match"
    < 65    -> "Low Match"
    None    -> None (not yet scored)
    """
    if score is None:
        return None
    if score >= 95:
        return "Excellent Match"
    if score >= 80:
        return "Strong Match"
    if score >= 65:
        return "Potential Match"
    return "Low Match"

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class JobNotFoundError(Exception):
    """Raised when job_id does not match any row."""


class NoResumeError(Exception):
    """Raised when no active resume exists in DB for this user."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_job(job_id: str, db: Session, user_id: uuid.UUID | str | None = None) -> dict:
    """
    Score a job against the user's active resume.

    Cache hit   → return stored result from UserJob, cached=True,  needs_rescore=False
    Stale score → return stored result from UserJob, cached=True,  needs_rescore=True
    Cache miss  → call Gemini, persist to UserJob, return result, cached=False

    Raises:
        JobNotFoundError  — job_id not found
        NoResumeError     — no resume in DB for user
        AIError           — Gemini call failed after retries
    """
    job = _get_job(job_id, db)
    resume = _get_active_resume(db, user_id)
    uid = user_id or resume.user_id
    user_job = _get_or_create_user_job(job, uid, db)

    cache_state = _check_cache(user_job, resume)

    if cache_state == "hit":
        logger.info("score_job cache=hit job_id=%s user_id=%s", job_id, uid)
        return _build_response(user_job, cached=True, needs_rescore=False)

    if cache_state == "stale":
        logger.info("score_job cache=stale job_id=%s user_id=%s", job_id, uid)
        return _build_response(user_job, cached=True, needs_rescore=True)

    # cache miss — call Gemini
    logger.info("score_job cache=miss job_id=%s user_id=%s — calling Gemini", job_id, uid)
    result = _call_gemini(job, resume)
    _persist_score(user_job, resume, result, db)

    return _build_response(user_job, cached=False, needs_rescore=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_job(job_id: str, db: Session) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found")
    return job


def _get_active_resume(db: Session, user_id: uuid.UUID | str | None = None) -> Resume:
    query = db.query(Resume)
    if user_id is not None:
        query = query.filter(Resume.user_id == user_id)
    resume = query.order_by(Resume.uploaded_at.desc()).first()
    if resume is None:
        raise NoResumeError("No active resume — upload a resume before scoring")
    return resume


def _get_or_create_user_job(job: Job, user_id: uuid.UUID | str, db: Session) -> UserJob:
    user_job = db.scalar(
        select(UserJob).where(
            UserJob.job_id == job.id,
            UserJob.user_id == user_id,
        )
    )
    if user_job is None:
        now = datetime.now(timezone.utc)
        user_job = UserJob(
            id=uuid.uuid4(),
            user_id=user_id,
            job_id=job.id,
            status="saved",
            created_at=now,
            updated_at=now,
        )
        db.add(user_job)
        db.commit()
        db.refresh(user_job)
    return user_job


def _check_cache(user_job: UserJob, resume: Resume) -> str:
    """
    Returns:
        "hit"    — score exists and was computed against user's current resume
        "stale"  — score exists but user's resume has since been replaced
        "miss"   — no score yet
    """
    if user_job.match_score is None:
        return "miss"

    if user_job.resume_uploaded_at == resume.uploaded_at:
        return "hit"

    return "stale"


def _call_gemini(job: Job, resume: Resume) -> dict:
    """
    Call GeminiClient.match_job(). Propagates AIError on failure.
    Returns raw MatchResult dict from client.
    """
    skills: list[str] = resume.skills or []
    description: str = job.description or ""

    client = GeminiClient()
    return client.match_job(description, skills)


def _persist_score(
    user_job: UserJob,
    resume: Resume,
    result: dict,
    db: Session,
) -> None:
    """Write score fields to user_job row and commit."""
    user_job.match_score = result["match_score"]
    user_job.missing_skills = result.get("missing_skills", [])
    user_job.match_summary = result.get("match_summary", "")
    user_job.matched_at = datetime.now(timezone.utc)
    user_job.resume_uploaded_at = resume.uploaded_at
    user_job.updated_at = datetime.now(timezone.utc)

    db.add(user_job)
    db.commit()
    db.refresh(user_job)

    logger.info(
        "score persisted user_job_id=%s score=%s user_id=%s",
        user_job.id,
        user_job.match_score,
        user_job.user_id,
    )


def _build_response(user_job: UserJob, *, cached: bool, needs_rescore: bool) -> dict:
    """Serialise user_job score fields into response dict."""
    return {
        "match_score": user_job.match_score,
        "missing_skills": user_job.missing_skills or [],
        "match_summary": user_job.match_summary or "",
        "matched_at": user_job.matched_at,
        "cached": cached,
        "needs_rescore": needs_rescore,
        "recommendation_label": recommendation_label(user_job.match_score),
    }