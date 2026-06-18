"""
Resume ORM model.

Maps to the `resumes` table defined in docs/DATABASE.md.

Design decisions (from DATABASE.md):
  - No foreign keys. Resume is standalone. Job scoring reads the active
    resume at call time and stores resume.uploaded_at on the job record
    (as job.resume_uploaded_at). There is no live FK dependency after
    scoring completes.
  - Only one row is expected at any time. resume_service.upload_resume()
    deletes the existing row before inserting a new one. No versioning,
    no history, no soft delete — all out of MVP scope.
  - `skills` is JSONB: a flat array of normalised skill strings produced
    by Gemini during upload. ["Python", "FastAPI", "PostgreSQL", ...]
  - `raw_text` stores the full PyMuPDF extraction. Kept so that if the
    Gemini skill extraction prompt is improved, re-extraction can run
    without re-uploading the PDF.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Resume(Base):
    """
    Represents the single active resume.

    Created by resume_service.upload_resume().
    Read by match_service.score_job() to get skills for Gemini.
    Deleted and replaced on every new upload.
    """

    __tablename__ = "resumes"

    # ── Identity ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        doc="Primary key — PostgreSQL-generated UUID.",
    )

    # ── File metadata ────────────────────────────────────────────────────────
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original filename of the uploaded PDF, e.g. 'john_doe_resume_2025.pdf'.",
    )

    # ── Extracted content ────────────────────────────────────────────────────
    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc=(
            "Full text extracted from the PDF by PyMuPDF. "
            "Stored so skill re-extraction can run without re-uploading the PDF "
            "if the Gemini prompt is improved."
        ),
    )

    skills: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        doc=(
            "Flat array of normalised technical skill strings from Gemini. "
            'Example: ["Python", "FastAPI", "PostgreSQL", "React", "TypeScript"]. '
            "Up to 30 items. Used as input for job match scoring."
        ),
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc=(
            "Timestamp when this resume was uploaded. "
            "Copied to job.resume_uploaded_at at scoring time to enable "
            "stale-score detection: if resume.uploaded_at > job.resume_uploaded_at "
            "then the job's score was produced against an older resume."
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Resume id={self.id} filename={self.filename!r} "
            f"skills={len(self.skills)} uploaded_at={self.uploaded_at}>"
        )

    @property
    def skill_count(self) -> int:
        """Return number of extracted skills."""
        return len(self.skills) if self.skills else 0