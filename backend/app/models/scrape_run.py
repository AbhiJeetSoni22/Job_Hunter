"""
ScrapeRun ORM model.

Maps to the `scrape_runs` table defined in docs/DATABASE.md.

Design decisions (from DATABASE.md):
  - One row per source per sync attempt (not one row per full sync run).
    This means a single "Sync Jobs" click produces two rows: one for
    remoteok, one for yc_jobs. Each row is independent — one can succeed
    while the other fails.
  - `completed_at` is NULL while a run is in progress or if the scraper
    crashed before finishing. scraper_service sets it on completion.
  - `error` is NULL on success, a string error message on failure.
    A row can have both jobs_found > 0 AND an error (partial success:
    some jobs scraped before the crash).

Used by:
  - GET /api/scraper/status  → returns last run per source
  - POST /api/scraper/run    → writes a row per source on completion
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

SCRAPER_SOURCE_VALUES: tuple[str, ...] = (
    "remoteok",
    "yc_jobs",
)


class ScrapeRun(Base):
    """
    Log entry for a single scraper execution against one source.

    Created by scraper_service.log_scrape_run() at the end of each
    source scrape, regardless of success or failure.
    """

    __tablename__ = "scrape_runs"

    # ── Identity ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        doc="Primary key — PostgreSQL-generated UUID.",
    )

    # ── Run metadata ─────────────────────────────────────────────────────────
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc=f"Which scraper produced this run. One of: {SCRAPER_SOURCE_VALUES}",
    )

    jobs_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        doc="Total number of jobs returned by the source before deduplication.",
    )

    jobs_new: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        doc=(
            "Number of jobs actually inserted into the jobs table. "
            "jobs_found - jobs_new = duplicates skipped."
        ),
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc=(
            "Error message if the scraper raised an exception, otherwise NULL. "
            "A non-NULL error does not imply jobs_new == 0 — partial success is possible."
        ),
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Timestamp when scraper_service began this source's scrape.",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc=(
            "Timestamp when scraper_service finished this source's scrape. "
            "NULL if the scraper crashed before completing."
        ),
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        # GET /api/scraper/status queries: latest run per source
        Index(
        "idx_scrape_runs_source_started",
        "source",
        "started_at",
       ),
    )

    def __repr__(self) -> str:
        return (
            f"<ScrapeRun id={self.id} source={self.source!r} "
            f"jobs_new={self.jobs_new} error={self.error is not None} "
            f"started_at={self.started_at}>"
        )

    @property
    def succeeded(self) -> bool:
        """Return True if the run completed without error."""
        return self.error is None and self.completed_at is not None

    @property
    def duration_seconds(self) -> float | None:
        """Return elapsed seconds, or None if run didn't complete."""
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()