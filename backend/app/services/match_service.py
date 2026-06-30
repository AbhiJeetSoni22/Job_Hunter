"""
match_service.py — Phase 2C
Responsibility: AI job match scoring with resume-keyed cache.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.gemini_client import GeminiClient, AIError
from app.models.job import Job
from app.models.resume import Resume

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
    """Raised when no active resume exists in DB."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_job(job_id: str, db: Session) -> dict:
    """
    Score a job against the active resume.

    Cache hit   → return stored result, cached=True,  needs_rescore=False
    Stale score → return stored result, cached=True,  needs_rescore=True
    Cache miss  → call Gemini, persist, return result, cached=False

    Raises:
        JobNotFoundError  — job_id not found
        NoResumeError     — no resume in DB
        AIError           — Gemini call failed after retries
    """
    job = _get_job(job_id, db)
    resume = _get_active_resume(db)

    cache_state = _check_cache(job, resume)

    if cache_state == "hit":
        logger.info("score_job cache=hit job_id=%s", job_id)
        return _build_response(job, cached=True, needs_rescore=False)

    if cache_state == "stale":
        logger.info("score_job cache=stale job_id=%s", job_id)
        return _build_response(job, cached=True, needs_rescore=True)

    # cache miss — call Gemini
    logger.info("score_job cache=miss job_id=%s — calling Gemini", job_id)
    result = _call_gemini(job, resume)
    _persist_score(job, resume, result, db)

    return _build_response(job, cached=False, needs_rescore=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_job(job_id: str, db: Session) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found")
    return job


def _get_active_resume(db: Session) -> Resume:
    resume = (
        db.query(Resume)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    if resume is None:
        raise NoResumeError("No active resume — upload a resume before scoring")
    return resume


def _check_cache(job: Job, resume: Resume) -> str:
    """
    Returns:
        "hit"    — score exists and was computed against current resume
        "stale"  — score exists but resume has since been replaced
        "miss"   — no score yet
    """
    if job.match_score is None:
        return "miss"

    if job.resume_uploaded_at == resume.uploaded_at:
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
    job: Job,
    resume: Resume,
    result: dict,
    db: Session,
) -> None:
    """Write score fields to job row and commit."""
    job.match_score = result["match_score"]
    job.missing_skills = result.get("missing_skills", [])
    job.match_summary = result.get("match_summary", "")
    job.matched_at = datetime.now(timezone.utc)
    job.resume_uploaded_at = resume.uploaded_at
    job.updated_at = datetime.now(timezone.utc)

    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(
        "score persisted job_id=%s score=%s",
        job.id,
        job.match_score,
    )


def _build_response(job: Job, *, cached: bool, needs_rescore: bool) -> dict:
    """Serialise job score fields into response dict."""
    return {
        "match_score": job.match_score,
        "missing_skills": job.missing_skills or [],
        "match_summary": job.match_summary or "",
        "matched_at": job.matched_at,
        "cached": cached,
        "needs_rescore": needs_rescore,
    }