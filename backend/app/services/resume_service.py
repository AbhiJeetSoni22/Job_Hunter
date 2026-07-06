"""
Resume service.

Owns all business logic for the `resumes` table:
    - Validating uploaded PDF files
    - Extracting text via PyMuPDF
    - Persisting the resume (delete-then-insert — single active resume)
    - Retrieving the latest resume or a specific resume by ID

    Architecture rules (ARCHITECTURE.md):
        - No HTTP concerns: no Request, no Response, no status codes.
        - Raise ValueError for validation failures.
        - Raise LookupError for not-found.
        - Routers translate these into HTTP responses.

        Phase 2B:
            Gemini skill extraction is now wired. After PDF text extraction, the service
            calls GeminiClient.extract_skills(). If Gemini fails (AIError or network),
            the resume is still stored with skills=[] — upload always succeeds.

            PyMuPDF import note:
                The package is installed as `pymupdf` but imported as `fitz`. This is
                expected — it is the same package. Do not attempt `import pymupdf`.
                """

import io
import logging
import re
import uuid
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.schemas.resume import ResumeResponse, ResumeTextResponse, ResumeUploadResponse
from app.ai.gemini_client import AIError, GeminiClient

logger = logging.getLogger(__name__)

# ── Validation constants ───────────────────────────────────────────────────

# Maximum PDF file size: 5 MB
MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024

# Allowed MIME types for PDF uploads
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "application/x-pdf",
})

# Minimum extracted text length to be considered a valid resume
MIN_TEXT_LENGTH: int = 100

# Maximum PDF page count — a real resume is rarely longer than this.
# Keeps processing cost bounded and rejects mis-uploaded documents
# (reports, transcripts, etc.) that would otherwise slip under the
# 5 MB size limit.
MAX_RESUME_PAGES: int = 20

# Common resume section headers used for a lightweight, non-blocking
# quality check (Optional Improvement #3). Matched case-insensitively
# as substrings of the extracted text — no NLP, no AI call.
RESUME_SECTION_KEYWORDS: tuple[str, ...] = (
    "experience",
    "work experience",
    "education",
    "skills",
    "projects",
    "certifications",
)


# ── Internal extraction result ─────────────────────────────────────────────

@dataclass(frozen=True)
class _ExtractionResult:
    """Intermediate result from PDF text extraction. Not exposed via API."""
    raw_text: str
    page_count: int
    char_count: int


    # ── Service class ──────────────────────────────────────────────────────────

class ResumeService:
    """
    Service for all resume-related operations.

    Instantiated per request with an injected SQLAlchemy session:
        service = ResumeService(db)
        """

    def __init__(self, db: Session) -> None:
        self._db = db

        # ── Upload ─────────────────────────────────────────────────────────────

    async def upload_resume(self, file: UploadFile) -> ResumeUploadResponse:
        """
        Validate, extract text from, and persist a PDF resume.

        Replaces any existing resume — only one active resume at a time.

        Args:
            file: FastAPI UploadFile from multipart/form-data.

            Returns:
                ResumeUploadResponse with id, filename, skills (empty in Phase 1D),
                uploaded_at, page_count, and char_count.

                Raises:
                    ValueError: if the file fails any validation check.
                    RuntimeError: if PyMuPDF fails to process the file.
                    """
        logger.info("ResumeService.upload_resume: started for file '%s'", file.filename)

        # ── Step 1: validate ───────────────────────────────────────────────
        filename = self._validate_file(file)

                    # ── Step 2: read bytes ─────────────────────────────────────────────
        content = await file.read()
        self._validate_size(content, filename)

                    # ── Step 3: extract text ───────────────────────────────────────────
        extraction = self._extract_text(content, filename)
        logger.info(
                        "ResumeService.upload_resume: extracted %d chars from %d pages — '%s'",
                        extraction.char_count,
                        extraction.page_count,
                        filename,
                    )

        # ── Step 4: extract skills via Gemini (graceful degradation) ────────
        skills = self._extract_skills_safe(extraction.raw_text)

        # ── Step 5: persist (delete old, insert new) ───────────────────────
        resume = self._persist(
            filename=filename,
            raw_text=extraction.raw_text,
            skills=skills,
            )
        logger.info(
            "ResumeService.upload_resume: saved resume id=%s filename='%s'",
            resume.id,
            filename,
        )

        return ResumeUploadResponse(
    id=resume.id,
    filename=resume.filename,
    skills=resume.skills,
    uploaded_at=resume.uploaded_at,
    page_count=extraction.page_count,
    char_count=extraction.char_count,
)

    def delete_latest(self) -> bool:
        """
        Delete the currently active resume.

        Returns:
            True  -> resume deleted
            False -> no resume exists
        """
        resume = self._query_latest()

        if resume is None:
                return False

        self._db.delete(resume)
        self._db.commit()

        logger.info(
            "ResumeService: deleted resume id=%s filename='%s'",
            resume.id,
            resume.filename,
        )

        return True

            # ── Read — latest ──────────────────────────────────────────────────────

    def get_latest(self) -> ResumeResponse:
        """
        Return the most recently uploaded resume.

        Raises:
            LookupError: if no resume has been uploaded yet.
            """
        resume = self._query_latest()
        if resume is None:
            raise LookupError("No resume uploaded")
        return ResumeResponse.model_validate(resume)

            # ── Read — by ID ───────────────────────────────────────────────────────

    def get_by_id(self, resume_id: uuid.UUID) -> ResumeResponse:
        """
        Return a resume by primary key.

        Args:
            resume_id: UUID of the resume to retrieve.

            Raises:
                LookupError: if no resume with that ID exists.
        """
        resume = self._db.get(Resume, resume_id)
        if resume is None:
            raise LookupError(f"Resume with id {resume_id} not found")
        return ResumeResponse.model_validate(resume)

                # ── Read — latest with raw text (used by match_service in Phase 2) ────

    def get_latest_with_text(self) -> ResumeTextResponse:
        """
        Return the latest resume including raw_text.

        Used internally by match_service to feed text to Gemini.
        Not exposed by a public endpoint (raw_text is large).

        Raises:
            LookupError: if no resume has been uploaded.
            """
        resume = self._query_latest()
        if resume is None:
            raise LookupError("No resume uploaded")
        return ResumeTextResponse.model_validate(resume)

            # ── Private: validation ────────────────────────────────────────────────

    def _validate_file(self, file: UploadFile) -> str:
        """
        Validate content type and filename. Return the sanitised filename.

        Raises:
            ValueError: on any validation failure.
            """
        if not file.filename:
            raise ValueError("Uploaded file has no filename")

        filename = file.filename.strip()

        # Content-type check (primary signal)
        content_type = (file.content_type or "").lower().strip()
        if content_type not in ALLOWED_CONTENT_TYPES:
                # Extension fallback: some clients send application/octet-stream
            if not filename.lower().endswith(".pdf"):
                raise ValueError(
                 f"File must be a PDF. Received content-type: '{content_type}'"
                )
            logger.debug(
                "ResumeService: content-type '%s' not in allowed set but "
                "filename ends with .pdf — proceeding",
                content_type,
            )

        return filename

    def _validate_size(self, content: bytes, filename: str) -> None:
        """
        Validate file is not empty and not above the size limit.

        Raises:
            ValueError: if the file is empty or exceeds MAX_FILE_SIZE_BYTES.
            """
        if len(content) == 0:
            raise ValueError(f"Uploaded file '{filename}' is empty")

        if len(content) > MAX_FILE_SIZE_BYTES:
            size_mb = len(content) / (1024 * 1024)
            raise ValueError(
            f"File '{filename}' is {size_mb:.1f} MB. "
            f"Maximum allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB"
        )

        # ── Private: PDF extraction ────────────────────────────────────────────

    def _extract_text(self, content: bytes, filename: str) -> _ExtractionResult:
        """
        Extract plain text from PDF bytes using PyMuPDF.

        Extraction strategy:
            - Opens the PDF from bytes (no disk I/O)
            - Iterates all pages and extracts text with layout preservation
            - Joins pages with double newline separator
            - Normalises whitespace (collapse runs of spaces/tabs)
            - Preserves paragraph breaks (double newlines)

            Raises:
                ValueError: if the PDF is encrypted, corrupted, or yields no text.
                RuntimeError: if PyMuPDF raises an unexpected error.
                """
        try:
            import fitz  # PyMuPDF — installed as 'pymupdf', imported as 'fitz'
        except ImportError as exc:
            raise RuntimeError(
                "PyMuPDF is not installed. Run: pip install pymupdf"
            ) from exc

        logger.debug("ResumeService: opening PDF '%s' (%d bytes)", filename, len(content))

        try:
            doc = fitz.open(stream=io.BytesIO(content), filetype="pdf")
        except Exception as exc:
            logger.warning(
                    "ResumeService: PyMuPDF failed to open '%s': %s", filename, exc
                )
            raise ValueError(
            f"Could not open '{filename}' as a PDF. "
            "The file may be corrupted or not a valid PDF."
        ) from exc

        # Reject encrypted PDFs that require a password
        if doc.is_encrypted:
            doc.close()
            raise ValueError(
              f"PDF '{filename}' is password-protected. "
              "Please upload an unencrypted PDF."
          )

        page_count = len(doc)
        logger.debug("ResumeService: PDF '%s' has %d pages", filename, page_count)

        # Reject resumes that are unrealistically long. Checked here — after
        # the PDF opens successfully — and before the per-page text loop, so
        # an oversized document doesn't pay the extraction cost for nothing.
        if page_count > MAX_RESUME_PAGES:
            doc.close()
            raise ValueError(
        f"Resume exceeds maximum allowed length ({MAX_RESUME_PAGES} pages). "
        "Please upload a shorter resume."
    )

        page_texts: list[str] = []

        for page_num in range(page_count):
            try:
                page = doc[page_num]
                # "text" mode preserves paragraph structure better than "blocks"
                page_text = page.get_text("text")
                if page_text.strip():
                    page_texts.append(page_text)
            except Exception as exc:
        # A single bad page should not abort the whole extraction
                logger.warning(
                    "ResumeService: failed to extract page %d from '%s': %s",
                    page_num + 1,
                    filename,
                    exc,
                )

        doc.close()

        if not page_texts:
            raise ValueError(
        f"This PDF ('{filename}') appears to contain only scanned images "
        "and no selectable text. Please upload a text-based PDF resume."
    )

        raw_text = self._normalise_text("\n\n".join(page_texts))

        if len(raw_text) < MIN_TEXT_LENGTH:
            raise ValueError(
        f"Extracted text from '{filename}' is too short ({len(raw_text)} chars). "
        "The PDF appears to contain minimal text content."
    )

        logger.debug(
            "ResumeService: extracted %d chars from %d/%d pages of '%s'",
            len(raw_text),
            len(page_texts),
            page_count,
            filename,
        )

        # Lightweight, non-blocking quality check (Optional Improvement #3).
        # Never rejects the upload — logging only.
        self._check_resume_sections(raw_text, filename)

        return _ExtractionResult(
            raw_text=raw_text,
            page_count=page_count,
            char_count=len(raw_text),
        )

    @staticmethod
    def _normalise_text(text: str) -> str:
        """
        Normalise extracted PDF text.

        Steps:
            1. Collapse horizontal whitespace (spaces/tabs) within lines
            2. Remove trailing whitespace from each line
            3. Collapse 3+ consecutive newlines into 2 (preserve paragraph breaks)
            4. Strip leading/trailing whitespace from the full document
            """
        # Collapse horizontal whitespace within lines
        text = re.sub(r"[ \t]+", " ", text)
        # Remove trailing whitespace from each line
        text = "\n".join(line.rstrip() for line in text.splitlines())
        # Collapse excessive blank lines (3+ newlines → 2)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _check_resume_sections(raw_text: str, filename: str) -> None:
        """
        Lightweight, non-blocking check for common resume section headers.

        Substring match against RESUME_SECTION_KEYWORDS, case-insensitive.
        Never raises — a document with unusual formatting or headers that
        don't match the list can still be a legitimate resume. This is a
        logging signal only, not a validation gate.
        """
        lowered = raw_text.lower()
        if not any(keyword in lowered for keyword in RESUME_SECTION_KEYWORDS):
            logger.warning(
                "ResumeService: uploaded document '%s' does not appear to "
                "contain common resume sections (experience/education/skills/"
                "projects/certifications)",
                filename,
            )

            # ── Private: persistence ───────────────────────────────────────────────

    def _persist(self, *, filename: str, raw_text: str, skills: list) -> Resume:
        """
        Delete any existing resume and insert a new one.

        Single-resume invariant: only one row in `resumes` at a time.
        Skills come from Gemini (Phase 2B); empty list on extraction failure.

        Returns the newly inserted Resume ORM instance.
        """
        # Delete existing resume if present
        existing = self._query_latest()
        if existing is not None:
            logger.info(
                "ResumeService: replacing existing resume id=%s", existing.id
            )
            self._db.delete(existing)
            self._db.flush()  # Ensure delete is sent before insert

        resume = Resume(
            filename=filename,
            raw_text=raw_text,
            skills=skills,
        )
        self._db.add(resume)
        self._db.commit()
        self._db.refresh(resume)

        return resume

    def _extract_skills_safe(self, raw_text: str) -> list[str]:
        """
        Call Gemini to extract skills. Returns [] on any failure.

        Graceful degradation: resume storage is always higher priority
        than AI enrichment. If Gemini is unavailable, the resume is
        stored with an empty skills list and can be re-extracted later.
        """
        logger.info("ResumeService: starting Gemini skill extraction")
        try:
            client = GeminiClient()
            skills = client.extract_skills(raw_text)
            logger.info(
                "ResumeService: Gemini extracted %d skills", len(skills)
            )
            return skills
        except AIError as exc:
            logger.error(
                "ResumeService: Gemini skill extraction failed after retries — "
                "storing resume with skills=[]. Error: %s",
                exc,
            )
            return []
        except Exception as exc:
            logger.error(
                "ResumeService: unexpected error during skill extraction — "
                "storing resume with skills=[]. Error: %s",
                exc,
                exc_info=True,
            )
        return []

    def _query_latest(self) -> Resume | None:
        """
        Return the most recently uploaded resume, or None.

        Sorted by uploaded_at DESC, limit 1.
        Under the single-resume invariant this will always be at most one row.
        """
        stmt = (
            select(Resume)
            .order_by(Resume.uploaded_at.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()