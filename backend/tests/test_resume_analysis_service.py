"""
test_resume_analysis_service.py

Tests for app.services.resume_analysis_service.ResumeAnalysisService.

Mirrors the mocking pattern used in tests/test_match_service.py:
    GeminiClient is patched at the import site inside the service module.
    """

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.ai.gemini_client import AIError
from app.services.resume_analysis_service import (
    MAX_JOB_DESCRIPTION_LENGTH,
    ResumeAnalysisService,
)
from tests.conftest import needs_db

pytestmark = needs_db


GEMINI_GAP_RESULT = {
    "match_score": 82,
    "summary": "Your profile aligns well with this role.",
    "missing_skills": ["AWS", "Docker"],
    "strengths": ["React", "Node.js"],
    "suggestions": ["Add deployment experience", "Mention testing frameworks"],
    "ats_tips": ["Highlight TypeScript experience", "Add CI/CD exposure"],
}


def _patch_gemini(result: dict | None = None, *, raises: Exception | None = None):
    mock_instance = MagicMock()
    if raises:
        mock_instance.analyze_resume_gap.side_effect = raises
    else:
        mock_instance.analyze_resume_gap.return_value = result or GEMINI_GAP_RESULT
        return patch(
    "app.services.resume_analysis_service.GeminiClient",
    return_value=mock_instance,
)


class TestValidAnalysis:

    def test_returns_structured_response(self, db, sample_resume):
        with _patch_gemini():
            result = ResumeAnalysisService(db).analyze(
                "We need a React and Node.js engineer with AWS experience."
            )

            assert result.match_score == 82
            assert result.summary == "Your profile aligns well with this role."
            assert result.missing_skills == ["AWS", "Docker"]
            assert result.strengths == ["React", "Node.js"]
            assert result.suggestions == [
                "Add deployment experience",
                "Mention testing frameworks",
            ]
            assert result.ats_tips == [
                "Highlight TypeScript experience",
                "Add CI/CD exposure",
            ]

    def test_calls_gemini_with_resume_text_and_jd(self, db, sample_resume):
        with _patch_gemini() as mock_ctor:
            ResumeAnalysisService(db).analyze("Looking for a Python developer.")
            mock_instance = mock_ctor.return_value
            mock_instance.analyze_resume_gap.assert_called_once()
            call_args = mock_instance.analyze_resume_gap.call_args
            assert call_args.args[0] == sample_resume.raw_text
            assert call_args.args[1] == "Looking for a Python developer."


class TestNoResume:

    def test_no_active_resume_raises_lookup_error(self, db):
        with _patch_gemini():
            with pytest.raises(LookupError, match="No resume uploaded"):
                ResumeAnalysisService(db).analyze("Some job description.")

    def test_gemini_not_called_when_no_resume(self, db):
        with _patch_gemini() as mock_ctor:
            with pytest.raises(LookupError):
                ResumeAnalysisService(db).analyze("Some job description.")
                mock_ctor.return_value.analyze_resume_gap.assert_not_called()


class TestEmptyJobDescription:

    def test_empty_string_raises_value_error(self, db, sample_resume):
        with pytest.raises(ValueError, match="must not be empty"):
            ResumeAnalysisService(db).analyze("")

    def test_whitespace_only_raises_value_error(self, db, sample_resume):
        with pytest.raises(ValueError, match="must not be empty"):
            ResumeAnalysisService(db).analyze("   \n\t  ")

    def test_gemini_not_called_for_empty_jd(self, db, sample_resume):
        with _patch_gemini() as mock_ctor:
            with pytest.raises(ValueError):
                ResumeAnalysisService(db).analyze("")
                mock_ctor.return_value.analyze_resume_gap.assert_not_called()


class TestLongJobDescription:

    def test_long_jd_is_truncated_not_rejected(self, db, sample_resume):
        long_jd = "Senior Engineer role. " * 2000
        assert len(long_jd) > MAX_JOB_DESCRIPTION_LENGTH

        with _patch_gemini() as mock_ctor:
            result = ResumeAnalysisService(db).analyze(long_jd)
            assert result.match_score == 82

            call_args = mock_ctor.return_value.analyze_resume_gap.call_args
            sent_jd = call_args.args[1]
            assert len(sent_jd) == MAX_JOB_DESCRIPTION_LENGTH

    def test_jd_within_limit_is_unchanged(self, db, sample_resume):
        normal_jd = "We need a backend engineer with Python experience."
        with _patch_gemini() as mock_ctor:
            ResumeAnalysisService(db).analyze(normal_jd)
            call_args = mock_ctor.return_value.analyze_resume_gap.call_args
            assert call_args.args[1] == normal_jd


class TestGeminiFailure:

    def test_ai_error_propagates(self, db, sample_resume):
        with _patch_gemini(raises=AIError("Gemini failed after 3 attempts")):
            with pytest.raises(AIError, match="Gemini failed"):
                ResumeAnalysisService(db).analyze("Some job description.")

    def test_value_error_from_gemini_propagates(self, db, sample_resume):
        with _patch_gemini(raises=ValueError("Could not parse JSON from Gemini response")):
            with pytest.raises(ValueError, match="Could not parse JSON"):
                ResumeAnalysisService(db).analyze("Some job description.")