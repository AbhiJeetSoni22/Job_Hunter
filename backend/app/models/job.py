"""
Job ORM model.

Maps to the `jobs` table defined in docs/DATABASE.md.

Design decisions (from DATABASE.md):
  - Match data (match_score, missing_skills, match_summary, matched_at,
    resume_uploaded_at) lives directly on this table — not a separate
    `matches` table. Single user, single resume: a join table adds
    complexity with zero benefit.
  - `status` and `notes` live here too. An `applications` table is the
    right abstraction for multi-user systems; for personal use the job
    record IS the application record.
  - `resume_uploaded_at` mirrors the resume's uploaded_at at scoring time.
    When resume.uploaded_at > job.resume_uploaded_at the UI can flag
    "Needs Re-score" without touching every job automatically.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# ---------------------------------------------------------------------------
# Allowed values for the status column.
# Stored as plain VARCHAR — no PostgreSQL enum type — so adding new values
# later never requires a migration that locks the table.
# Validation is enforced at the Pydantic schema layer.
# ---------------------------------------------------------------------------
JOB_STATUS_VALUES: tuple[str, ...] = (
    "saved",
    "applied",
    "interview",
    "offer",
    "rejected",
)

JOB_SOURCE_VALUES: tuple[str, ...] = (
    "remoteok",
    "yc_jobs",
)


class Job(Base):
    """
    Represents a single job listing.

    Populated by scrapers (Phase 1).
    Match fields populated by match_service (Phase 2).
    Status/notes populated by job_service via PATCH endpoint.
    """

    __tablename__ = "jobs"

    # ── Identity ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        doc="Primary key — PostgreSQL-generated UUID.",
    )

    # ── Job listing fields ──────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Job title as provided by the source.",
    )

    company: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Company name as provided by the source.",
    )

    company_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Company website URL. Not all sources provide this.",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full job description. Fed to Gemini for matching.",
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        doc="Canonical source URL. Used as the deduplication key across all scrapers.",
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc=f"Which scraper collected this job. One of: {JOB_SOURCE_VALUES}",
    )

    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="Location string as provided by the source. May be 'Remote', a city, or None.",
    )

    # ── Application tracking ─────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="saved",
        doc=f"Application tracking status. One of: {JOB_STATUS_VALUES}. Defaults to 'saved'.",
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Free-text notes. Contact name, next step, anything relevant.",
    )

    # ── AI match results (populated by match_service in Phase 2) ─────────────
    match_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Resume fit score 0–100 from Gemini. Null until scored.",
    )

    missing_skills: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Array of skill strings from Gemini. Up to 5 items. Null until scored.",
    )

    match_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Two-sentence fit summary from Gemini. Null until scored.",
    )

    matched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the last Gemini scoring call. Null until scored.",
    )

    resume_uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc=(
            "Copied from resume.uploaded_at at scoring time. "
            "If this is older than the current resume's uploaded_at, "
            "the score is stale and the UI should flag 'Needs Re-score'."
        ),
    )

    # ── Source timestamps ────────────────────────────────────────────────────
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Original posting date from the source. May be None if source doesn't provide it.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="Timestamp when this record was first inserted by a scraper.",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="Timestamp of the last update to any field on this record.",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        # Filter by application status (most common query filter)
        Index("idx_jobs_status", "status"),
        # Filter by source (remoteok vs yc_jobs)
        Index("idx_jobs_source", "source"),
        # Sort job list by match score descending; NULLs sort last
        Index("idx_jobs_score", "match_score")
        # Deduplication — enforced at DB level, not just application level
        # Defined as unique=True on the column above; named here for clarity
        # (The UNIQUE constraint creates the index automatically)
    )

    def __repr__(self) -> str:
        return (
            f"<Job id={self.id} title={self.title!r} "
            f"company={self.company!r} status={self.status!r} "
            f"score={self.match_score}>"
        )

    @property
    def is_scored(self) -> bool:
        """Return True if Gemini has produced a match score for this job."""
        return self.match_score is not None

    @property
    def needs_rescore(self, current_resume_uploaded_at: datetime | None = None) -> bool:
        """
        Return True if the score was produced against an older resume.

        This property is intentionally simple — match_service calls it
        with the current resume's uploaded_at when needed.
        """
        if not self.is_scored:
            return False
        if current_resume_uploaded_at is None:
            return False
        return (
            self.resume_uploaded_at is None
            or self.resume_uploaded_at < current_resume_uploaded_at
        )