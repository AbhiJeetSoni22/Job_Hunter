"""
Pydantic schemas for resume endpoints.

Three response shapes:
  - ResumeResponse      : standard resume record (id, filename, skills, uploaded_at)
  - ResumeUploadResponse: returned immediately after upload; includes page_count
                          and char_count so the client can show extraction stats
                          without a second request.
  - ResumeTextResponse  : full record including raw_text; used by internal
                          services (match_service) and optionally exposed for
                          debugging. NOT returned by default upload response
                          to keep the payload small.

Phase 1D:
  skills is returned as an empty list. Gemini skill extraction is wired
  in Phase 2B. The field exists in the schema now so the response shape
  does not change when skills are added — the client receives [] today
  and a populated list after Phase 2B without any breaking change.

Relationship to models:
  Schemas never import ORM models directly.
  Services call Resume.model_validate(orm_instance) to convert.
  All schemas use from_attributes=True for SQLAlchemy ORM compatibility.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Resume — standard response
# Returned by GET /api/resume/latest and GET /api/resume/{resume_id}.
# Does NOT include raw_text — that field can be large and is rarely needed
# by the frontend.
# ---------------------------------------------------------------------------

class ResumeResponse(BaseModel):
    """
    Standard resume record returned by read endpoints.

    Omits raw_text to keep the payload small. Use ResumeTextResponse
    when raw_text is needed (e.g. internal services, debug endpoint).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str = Field(..., description="Original uploaded PDF filename")
    skills: list[Any] = Field(
        default_factory=list,
        description=(
            "Extracted technical skills. Empty list until Phase 2 Gemini "
            "integration is complete."
        ),
    )
    uploaded_at: datetime = Field(..., description="UTC timestamp of upload")


# ---------------------------------------------------------------------------
# Resume — upload response
# Returned immediately after POST /api/resume.
# Includes extraction statistics (page_count, char_count) so the client
# can show feedback without a second round-trip.
# ---------------------------------------------------------------------------

class ResumeUploadResponse(BaseModel):
    """
    Response returned after a successful PDF upload and text extraction.

    Includes extraction metadata (page_count, char_count) in addition to
    the standard resume fields, so the UI can show "Extracted 3 pages,
    4,200 characters" immediately after upload.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str = Field(..., description="Original uploaded PDF filename")
    skills: list[Any] = Field(
        default_factory=list,
        description=(
            "Extracted technical skills. Empty list in Phase 1D. "
            "Populated after Phase 2B Gemini skill extraction."
        ),
    )
    uploaded_at: datetime = Field(..., description="UTC timestamp of upload")

    # Extraction metadata — not stored in DB, computed during upload
    page_count: int = Field(..., ge=0, description="Number of pages extracted from PDF")
    char_count: int = Field(
        ..., ge=0, description="Number of characters in extracted text"
    )


# ---------------------------------------------------------------------------
# Resume — full text response
# Includes raw_text. Used by internal services and optionally by a
# debug/admin endpoint. Not returned by the standard upload or read paths.
# ---------------------------------------------------------------------------

class ResumeTextResponse(BaseModel):
    """
    Full resume record including raw extracted text.

    Used internally by match_service to get the text for Gemini.
    May be exposed via a debug endpoint; never returned by default
    read endpoints (raw_text can be very large).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    raw_text: str = Field(..., description="Full text extracted from the PDF by PyMuPDF")
    skills: list[Any] = Field(default_factory=list)
    uploaded_at: datetime