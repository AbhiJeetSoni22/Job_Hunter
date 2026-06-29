"""
test_match_service.py

Tests for app.services.match_service (module-level functions).

score_job(job_id: str, db: Session) -> dict

job_id must be a valid UUID string — PostgreSQL rejects non-UUID strings
with "invalid input syntax for type uuid".
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.match_service import score_job
from tests.conftest import needs_db

pytestmark = needs_db


GEMINI_MATCH_RESULT = {
    "match_score": 80,
    "missing_skills": ["Docker", "Kubernetes"],
    "match_summary": "Strong Python fit. Missing container skills.",
}


def _patch_gemini(match_result: dict = None, *, raises=None):
    result = match_result or GEMINI_MATCH_RESULT
    mock_instance = MagicMock()
    if raises:
        mock_instance.match_job.side_effect = raises
    else:
        mock_instance.match_job.return_value = result
    return patch("app.services.match_service.GeminiClient", return_value=mock_instance)


# ---------------------------------------------------------------------------
# JobNotFoundError / NoResumeError
# ---------------------------------------------------------------------------

class TestScoreJobErrors:

   

    def test_job_not_found_raises(self, db):
        from app.services.match_service import score_job, JobNotFoundError

        # Must be valid UUID format — PG rejects non-UUID strings
        missing_id = str(uuid.uuid4())
        with pytest.raises(JobNotFoundError, match="not found"):
            score_job(missing_id, db)

    def test_no_resume_raises(self, db, sample_job):
        from app.services.match_service import score_job, NoResumeError

        with pytest.raises(NoResumeError, match="No active resume"):
            score_job(str(sample_job.id), db)


# ---------------------------------------------------------------------------
# Cache miss
# ---------------------------------------------------------------------------

class TestCacheMiss:

    @pytest.fixture
    def uncached_job(self, db, sample_job):
        sample_job.match_score = None
        sample_job.match_summary = None
        sample_job.missing_skills = None
        db.commit()
        db.refresh(sample_job)
        return sample_job

    def test_cache_miss_calls_gemini(
        self,
        db,
        uncached_job,
        sample_resume,
    ):
        with _patch_gemini() as MockGemini:
            score_job(str(uncached_job.id), db)

            MockGemini.return_value.match_job.assert_called_once()

    def test_cache_miss_returns_correct_score(self, db, sample_job, sample_resume):
        from app.services.match_service import score_job

        custom = {"match_score": 73, "missing_skills": ["Go"], "match_summary": "Good fit."}
        with _patch_gemini(custom):
            result = score_job(str(sample_job.id), db)

        assert result["match_score"] == 73
        assert result["missing_skills"] == ["Go"]
        assert result["match_summary"] == "Good fit."
        assert isinstance(result["matched_at"], datetime)

    def test_cache_miss_persists_score_to_db(self, db, sample_job, sample_resume):
        from app.services.match_service import score_job
        from app.models.job import Job

        with _patch_gemini():
            score_job(str(sample_job.id), db)

        refreshed = db.get(Job, str(sample_job.id))
        assert refreshed.match_score == GEMINI_MATCH_RESULT["match_score"]
        assert refreshed.missing_skills == GEMINI_MATCH_RESULT["missing_skills"]
        assert refreshed.resume_uploaded_at == sample_resume.uploaded_at

    def test_ai_error_propagates(self, db, sample_job, sample_resume):
        from app.services.match_service import score_job
        from app.ai.gemini_client import AIError

        with _patch_gemini(raises=AIError("quota exceeded")):
            with pytest.raises(AIError):
                score_job(str(sample_job.id), db)


# ---------------------------------------------------------------------------
# Cache hit
# ---------------------------------------------------------------------------

class TestCacheHit:

    def test_cache_hit_does_not_call_gemini(self, db, scored_job, sample_resume):
        from app.services.match_service import score_job

        # Align resume.uploaded_at with scored_job so cache check returns "hit"
        sample_resume.uploaded_at = scored_job.resume_uploaded_at
        db.add(sample_resume)
        db.commit()

        with patch("app.services.match_service.GeminiClient") as MockGemini:
            result = score_job(str(scored_job.id), db)
            assert not MockGemini.return_value.match_job.called

        assert result["cached"] is True
        assert result["needs_rescore"] is False

    def test_cache_hit_returns_stored_score(self, db, scored_job, sample_resume):
        from app.services.match_service import score_job

        sample_resume.uploaded_at = scored_job.resume_uploaded_at
        db.add(sample_resume)
        db.commit()

        with patch("app.services.match_service.GeminiClient"):
            result = score_job(str(scored_job.id), db)

        assert result["match_score"] == scored_job.match_score


# ---------------------------------------------------------------------------
# Stale cache
# ---------------------------------------------------------------------------

class TestStaleCache:

    def test_stale_does_not_call_gemini(self, db, scored_job, sample_resume):
        from app.services.match_service import score_job

        # sample_resume.uploaded_at != scored_job.resume_uploaded_at → stale
        assert sample_resume.uploaded_at != scored_job.resume_uploaded_at

        with patch("app.services.match_service.GeminiClient") as MockGemini:
            result = score_job(str(scored_job.id), db)
            assert not MockGemini.return_value.match_job.called

        assert result["cached"] is True
        assert result["needs_rescore"] is True

    def test_stale_returns_existing_score(self, db, scored_job, sample_resume):
        from app.services.match_service import score_job

        with patch("app.services.match_service.GeminiClient"):
            result = score_job(str(scored_job.id), db)

        assert result["match_score"] == scored_job.match_score


# ---------------------------------------------------------------------------
# Response dict shape
# ---------------------------------------------------------------------------

class TestResponseShape:

    def test_response_has_all_expected_keys(self, db, sample_job, sample_resume):
        from app.services.match_service import score_job

        with _patch_gemini():
            result = score_job(str(sample_job.id), db)

        expected = {"match_score", "missing_skills", "match_summary", "matched_at", "cached", "needs_rescore"}
        assert expected.issubset(result.keys())

    def test_missing_skills_is_list(self, db, sample_job, sample_resume):
        from app.services.match_service import score_job

        with _patch_gemini():
            result = score_job(str(sample_job.id), db)

        assert isinstance(result["missing_skills"], list)

    def test_match_summary_is_str(self, db, sample_job, sample_resume):
        from app.services.match_service import score_job

        with _patch_gemini():
            result = score_job(str(sample_job.id), db)

        assert isinstance(result["match_summary"], str)