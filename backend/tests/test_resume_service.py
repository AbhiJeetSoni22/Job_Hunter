"""
test_resume_service.py

Tests for app.services.resume_service.ResumeService.

Patch strategy:
  - GeminiClient: top-level import → patch "app.services.resume_service.GeminiClient"
  - fitz: LOCAL import inside _extract_text() → patch via sys.modules["fitz"]
    (module-level patch won't work; must inject into sys.modules before the
    method runs so `import fitz` resolves to the mock)
"""

from __future__ import annotations

import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import needs_db


# ---------------------------------------------------------------------------
# fitz mock factory
# ---------------------------------------------------------------------------

def _make_fitz_mock(page_text: str = None, page_count: int = 2):
    """
    Build a sys.modules-injectable fitz mock.
    Returns (mock_fitz_module, context_manager).
    """
    if page_text is None:
        page_text = "Software Engineer with Python FastAPI experience. " * 10

    mock_page = MagicMock()
    mock_page.get_text.return_value = page_text

    mock_doc = MagicMock()
    mock_doc.__len__ = MagicMock(return_value=page_count)
    mock_doc.is_encrypted = False
    mock_doc.__getitem__ = MagicMock(return_value=mock_page)

    mock_fitz = MagicMock()
    mock_fitz.open.return_value = mock_doc

    return mock_fitz


class fitz_patched:
    """Context manager: inject mock fitz into sys.modules for the duration."""

    def __init__(self, page_text: str = None, page_count: int = 2):
        self.mock = _make_fitz_mock(page_text, page_count)

    def __enter__(self):
        sys.modules["fitz"] = self.mock
        return self.mock

    def __exit__(self, *_):
        sys.modules.pop("fitz", None)


# ---------------------------------------------------------------------------
# Pure-logic tests (no DB required)
# ---------------------------------------------------------------------------

class TestValidateFile:

    def _svc(self):
        from app.services.resume_service import ResumeService
        return ResumeService(db=MagicMock())

    def _file(self, filename, content_type):
        m = MagicMock()
        m.filename = filename
        m.content_type = content_type
        return m

    def test_valid_pdf_content_type(self):
        result = self._svc()._validate_file(self._file("resume.pdf", "application/pdf"))
        assert result == "resume.pdf"

    def test_alternative_pdf_content_type(self):
        result = self._svc()._validate_file(self._file("resume.pdf", "application/x-pdf"))
        assert result == "resume.pdf"

    def test_octet_stream_with_pdf_extension_allowed(self):
        result = self._svc()._validate_file(self._file("resume.pdf", "application/octet-stream"))
        assert result == "resume.pdf"

    def test_octet_stream_non_pdf_extension_raises(self):
        with pytest.raises(ValueError, match="must be a PDF"):
            self._svc()._validate_file(self._file("resume.docx", "application/octet-stream"))

    def test_empty_filename_raises(self):
        with pytest.raises(ValueError, match="no filename"):
            self._svc()._validate_file(self._file("", "application/pdf"))

    def test_none_filename_raises(self):
        m = MagicMock()
        m.filename = None
        m.content_type = "application/pdf"
        with pytest.raises(ValueError, match="no filename"):
            self._svc()._validate_file(m)


class TestValidateSize:

    def _svc(self):
        from app.services.resume_service import ResumeService
        return ResumeService(db=MagicMock())

    def test_valid_size_no_raise(self):
        self._svc()._validate_size(b"x" * 100, "resume.pdf")

    def test_empty_file_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self._svc()._validate_size(b"", "resume.pdf")

    def test_oversized_file_raises(self):
        from app.services.resume_service import MAX_FILE_SIZE_BYTES
        with pytest.raises(ValueError, match="MB"):
            self._svc()._validate_size(b"x" * (MAX_FILE_SIZE_BYTES + 1), "resume.pdf")

    def test_exactly_at_limit_no_raise(self):
        from app.services.resume_service import MAX_FILE_SIZE_BYTES
        self._svc()._validate_size(b"x" * MAX_FILE_SIZE_BYTES, "resume.pdf")


class TestExtractSkillsSafe:

    def _svc(self):
        from app.services.resume_service import ResumeService
        return ResumeService(db=MagicMock())

    def test_returns_skills_on_success(self):
        with patch("app.services.resume_service.GeminiClient") as MockClass:
            MockClass.return_value.extract_skills.return_value = ["Python", "FastAPI"]
            result = self._svc()._extract_skills_safe("some resume text")
        assert result == ["Python", "FastAPI"]

    def test_returns_empty_list_on_ai_error(self):
        from app.ai.gemini_client import AIError
        with patch("app.services.resume_service.GeminiClient") as MockClass:
            MockClass.return_value.extract_skills.side_effect = AIError("fail")
            result = self._svc()._extract_skills_safe("some resume text")
        assert result == []

    def test_returns_empty_list_on_unexpected_error(self):
        with patch("app.services.resume_service.GeminiClient") as MockClass:
            MockClass.return_value.extract_skills.side_effect = RuntimeError("boom")
            result = self._svc()._extract_skills_safe("some resume text")
        assert result == []


# ---------------------------------------------------------------------------
# DB tests
# ---------------------------------------------------------------------------

skip_no_db = pytest.mark.skipif(
    not __import__("os").environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set",
)


@skip_no_db
class TestGetLatest:

    def test_raises_when_no_resume(self, resume_service):
        with pytest.raises(LookupError, match="No resume"):
            resume_service.get_latest()

    def test_returns_resume_response(self, resume_service, sample_resume):
        from app.schemas.resume import ResumeResponse
        result = resume_service.get_latest()
        assert isinstance(result, ResumeResponse)
        assert result.filename == "john_doe_resume.pdf"

    def test_no_raw_text_in_response(self, resume_service, sample_resume):
        result = resume_service.get_latest()
        assert not hasattr(result, "raw_text")


@skip_no_db
class TestGetById:

    def test_returns_resume_response(self, resume_service, sample_resume):
        from app.schemas.resume import ResumeResponse
        result = resume_service.get_by_id(sample_resume.id)
        assert isinstance(result, ResumeResponse)
        assert str(result.id) == str(sample_resume.id)

    def test_not_found_raises_lookup_error(self, resume_service):
        with pytest.raises(LookupError, match="not found"):
            resume_service.get_by_id(uuid.uuid4())


@skip_no_db
class TestGetLatestWithText:

    def test_includes_raw_text(self, resume_service, sample_resume):
        from app.schemas.resume import ResumeTextResponse
        result = resume_service.get_latest_with_text()
        assert isinstance(result, ResumeTextResponse)
        assert len(result.raw_text) > 0

    def test_raises_when_no_resume(self, resume_service):
        with pytest.raises(LookupError, match="No resume"):
            resume_service.get_latest_with_text()


@skip_no_db
class TestDeleteLatest:

    def test_returns_false_when_no_resume(self, resume_service):
        assert resume_service.delete_latest() is False

    def test_returns_true_and_removes_resume(self, resume_service, sample_resume):
        assert resume_service.delete_latest() is True
        with pytest.raises(LookupError):
            resume_service.get_latest()

    def test_idempotent_second_delete(self, resume_service, sample_resume):
        resume_service.delete_latest()
        assert resume_service.delete_latest() is False


@skip_no_db
class TestUploadResume:

    def _file(
        self,
        filename: str = "resume.pdf",
        content_type: str = "application/pdf",
        content: bytes = b"fake-pdf-content",
    ):
        m = MagicMock()
        m.filename = filename
        m.content_type = content_type
        m.read = AsyncMock(return_value=content)
        return m

    @pytest.mark.asyncio
    async def test_upload_happy_path(self, resume_service):
        with fitz_patched():
            with patch("app.services.resume_service.GeminiClient") as MockGemini:
                MockGemini.return_value.extract_skills.return_value = ["Python"]
                result = await resume_service.upload_resume(self._file())

        from app.schemas.resume import ResumeUploadResponse
        assert isinstance(result, ResumeUploadResponse)
        assert result.filename == "resume.pdf"
        assert result.page_count == 2
        assert result.char_count > 0

    @pytest.mark.asyncio
    async def test_upload_replaces_existing_resume(self, resume_service, sample_resume):
        with fitz_patched():
            with patch("app.services.resume_service.GeminiClient") as MockGemini:
                MockGemini.return_value.extract_skills.return_value = []
                await resume_service.upload_resume(self._file(filename="new_resume.pdf"))

        result = resume_service.get_latest()
        assert result.filename == "new_resume.pdf"

    @pytest.mark.asyncio
    async def test_upload_wrong_content_type_raises(self, resume_service):
        with pytest.raises(ValueError, match="must be a PDF"):
            await resume_service.upload_resume(
                self._file(filename="resume.docx", content_type="application/msword")
            )

    @pytest.mark.asyncio
    async def test_upload_empty_file_raises(self, resume_service):
        with pytest.raises(ValueError, match="empty"):
            await resume_service.upload_resume(self._file(content=b""))

    @pytest.mark.asyncio
    async def test_upload_skills_empty_when_gemini_fails(self, resume_service):
        from app.ai.gemini_client import AIError
        with fitz_patched():
            with patch("app.services.resume_service.GeminiClient") as MockGemini:
                MockGemini.return_value.extract_skills.side_effect = AIError("quota")
                result = await resume_service.upload_resume(self._file())
        assert result.skills == []

    @pytest.mark.asyncio
    async def test_upload_stores_skills_from_gemini(self, resume_service):
        with fitz_patched():
            with patch("app.services.resume_service.GeminiClient") as MockGemini:
                MockGemini.return_value.extract_skills.return_value = ["Python", "FastAPI", "Docker"]
                result = await resume_service.upload_resume(self._file())
        assert "Python" in result.skills
        assert "FastAPI" in result.skills