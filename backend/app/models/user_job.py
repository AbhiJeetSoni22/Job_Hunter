"""
UserJob ORM model (Application tracking and per-user match analysis).

Maps to the `user_jobs` table.

Architecture:
    - Jobs are global scraped listings deduplicated by canonical URL.
    - All user-specific tracking (status, notes) and AI match results
      (match_score, missing_skills, match_summary, matched_at, resume_uploaded_at)
      live on this UserJob model.
    - One row per (user_id, job_id) pair.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.job import JOB_STATUS_VALUES


class UserJob(Base):
    """
    Represents a user's personal relationship and application state for a specific job listing.
    """

    __tablename__ = "user_jobs"

    # ── Identity ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        doc="Primary key — PostgreSQL-generated UUID.",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to the user owning this job record.",
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to the global job listing.",
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
        doc="User's personal free-text notes for this job.",
    )

    # ── AI match results (scored against this user's active resume) ─────────
    match_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Resume fit score 0–100 from Gemini for this user. Null until scored.",
    )

    missing_skills: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Array of skill strings missing for this user. Null until scored.",
    )

    match_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Fit summary from Gemini for this user. Null until scored.",
    )

    matched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the last Gemini scoring call for this user. Null until scored.",
    )

    resume_uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc=(
            "Copied from the user's resume.uploaded_at at scoring time. "
            "Used to detect stale scores when user uploads a newer resume."
        ),
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="Timestamp when this user-job record was first created.",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="Timestamp when this user-job record was last modified.",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    user = relationship("User", back_populates="user_jobs")
    job = relationship("Job", back_populates="user_jobs")

    # ── Constraints & Indexes ────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_jobs_user_id_job_id"),
        Index("idx_user_jobs_job_id", "job_id"),
        Index("idx_user_jobs_user_id", "user_id"),
        Index("idx_user_jobs_user_status", "user_id", "status"),
        Index("idx_user_jobs_user_score", "user_id", "match_score"),
    )

    def __repr__(self) -> str:
        return (
            f"<UserJob id={self.id} user_id={self.user_id} job_id={self.job_id} "
            f"status={self.status!r} match_score={self.match_score}>"
        )
