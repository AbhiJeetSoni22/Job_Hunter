"""
Job ORM model.

Maps to the `jobs` table defined in docs/DATABASE.md.

Design decisions:
    - Global scraped listing: Stores shared, deduplicated job metadata across all users.
      Deduplicated globally by canonical `url` (UNIQUE constraint).
    - User-specific state (application status, notes, AI match score, missing skills,
      match summary, matched_at, resume_uploaded_at) lives in the `UserJob` relationship
      model (`user_jobs` table), scoped strictly per user.
    - Global Job records are never deleted when a user removes a job from their board;
      only that user's `UserJob` relationship is removed.
    - Cascades: If a global Job is deleted by system cleanup, all linked `user_jobs`
      are automatically cascaded via foreign key ON DELETE CASCADE.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # ── Lifecycle tracking (job expiry / cleanup) ────────────────────────────
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc=(
            "Timestamp this job's URL was last seen during a sync of its "
            "source. Reset to now() every time the job appears in a scrape; "
            "used together with missing_sync_count to detect stale listings."
        ),
    )

    missing_sync_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        doc=(
            "Consecutive syncs of this job's source where the job's URL was "
            "not seen. Reset to 0 whenever the job is seen again. Jobs "
            "reaching 2 are marked expired."
        ),
    )

    expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc=(
            "Set once missing_sync_count reaches 2 during a sync of this "
            "job's source. Null while active. Cleared automatically if the "
            "job's URL reappears in a later sync (job becomes active again)."
        ),
    )

    # ── Relationships ────────────────────────────────────────────────────────
    user_jobs = relationship("UserJob", back_populates="job", cascade="all, delete-orphan")

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        # Filter by source (remoteok vs yc_jobs)
        Index("idx_jobs_source", "source"),
        # Default listing excludes expired jobs; cleanup scans by expired_at
        Index("idx_jobs_expired_at", "expired_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Job id={self.id} title={self.title!r} "
            f"company={self.company!r} source={self.source!r}>"
        )