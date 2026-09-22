"""
ScoringRun ORM model.

Maps to the `scoring_runs` table.

WHY THIS MODEL EXISTS:
    POST /api/scraper/run schedules background auto-scoring of newly
    inserted jobs (see routers/scraper.py, ScraperService.run_auto_score).
    The frontend needs to know when that background work reaches a
    *terminal* state so it can stop polling and refresh the dashboard.

    match_score IS NOT NULL on the jobs table is NOT sufficient to detect
    this: a job whose Gemini call fails (AIError) is intentionally left
    with match_score = NULL forever (see match_service.score_job /
    ScraperService._auto_score_new_jobs, which logs and continues past
    per-job AIError). Polling "how many of these jobs have a score" would
    therefore never terminate if even one job's scoring permanently fails.

    ScoringRun instead tracks the batch itself: how many jobs it covers,
    how many were scored, and how many failed. The batch is "completed"
    exactly when scored + failed == total_jobs — regardless of whether
    every individual job succeeded.

Design decisions:
    - One row per POST /api/scraper/run call that finds at least one new
      job (no row is created when total_new == 0 — nothing to track).
    - status is a plain VARCHAR ("running" | "completed"), not a Postgres
      enum, for the same reason as Job.status: new values later shouldn't
      require a migration that locks the table.
    - scored_jobs / failed_jobs are updated after each job as the
      background task progresses (not just once at the end), so polling
      can show live "Scoring 1/2..." progress, not just a final result.
    - completed_at is NULL while running; set once status flips to
      "completed". Distinct from Job.matched_at, which is per-job.
    - No global/in-process Python flag anywhere — status lives entirely
      in this table, so it's correct even across server restarts or
      multiple worker processes.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

SCORING_RUN_STATUS_VALUES: tuple[str, ...] = (
    "running",
    "completed",
)


class ScoringRun(Base):
    """
    Tracks one background auto-scoring batch (one POST /api/scraper/run
    with new jobs to score) for a specific user.

    Created by ScraperService.start_scoring_run() synchronously, in the
    same request that returns new_job_ids — before the background task
    is scheduled, so the row always exists by the time the frontend could
    possibly poll for it.

    Updated by ScraperService._auto_score_new_jobs() / run_auto_score()
    inside the background task, using a fresh SessionLocal() (never the
    request-scoped session — see routers/scraper.py).
    """

    __tablename__ = "scoring_runs"

    # ── Identity ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        doc="Primary key — PostgreSQL-generated UUID. Returned to the "
        "frontend as ScraperRunSummary.scoring_run_id.",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to the user who triggered this scoring run.",
    )

    # ── Progress / terminal state ─────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="running",
        doc=f"One of: {SCORING_RUN_STATUS_VALUES}. Terminal once 'completed'.",
    )

    total_jobs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Number of job ids scheduled for scoring in this batch.",
    )

    scored_jobs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        doc="Jobs successfully scored so far. Updated incrementally.",
    )

    failed_jobs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        doc=(
            "Jobs that will never be scored by this run — a permanent "
            "Gemini failure (AIError), a job that disappeared before "
            "scoring, or jobs left unattempted because the active resume "
            "was removed mid-run. Updated incrementally. "
            "status flips to 'completed' once scored_jobs + failed_jobs "
            "== total_jobs."
        ),
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="When this batch was scheduled (same request as the sync response).",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Set once status becomes 'completed'. NULL while running.",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    user = relationship("User", back_populates="scoring_runs")

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("idx_scoring_runs_status", "status"),
        Index("idx_scoring_runs_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScoringRun id={self.id} user_id={self.user_id} status={self.status!r} "
            f"scored={self.scored_jobs} failed={self.failed_jobs} "
            f"total={self.total_jobs}>"
        )

    @property
    def pending_jobs(self) -> int:
        """Jobs neither scored nor failed yet."""
        return self.total_jobs - self.scored_jobs - self.failed_jobs
