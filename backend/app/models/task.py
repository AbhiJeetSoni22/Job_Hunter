"""
Task ORM model for PostgreSQL task queue.

Maps to the `tasks` table.

WHY THIS MODEL EXISTS:
    Phase 1 replaces in-process FastAPI BackgroundTasks with a durable,
    PostgreSQL-backed task queue. Long-running scraping and AI scoring batches
    survive web-server restarts and can be processed by independent worker processes.

Design decisions:
    - id is UUID primary key generated via gen_random_uuid().
    - status transitions: queued -> running -> succeeded / failed (or cancelled).
    - claiming uses SELECT ... FOR UPDATE SKIP LOCKED.
    - worker leases: worker_id and lease_timeout_at ensure a dead worker's
      task is recovered, while preventing stale workers from overwriting newer attempts.
    - available_at enables delayed tasks and exponential backoff retry scheduling.
    - user_id is nullable (nullable for global scheduled runs, set for user tasks).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

TASK_STATUS_VALUES: tuple[str, ...] = (
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
)

TASK_TYPE_VALUES: tuple[str, ...] = (
    "scrape",
    "scoring",
    "bulk_score",
)


class Task(Base):
    """
    Durable background task row in the PostgreSQL queue.
    """

    __tablename__ = "tasks"

    # ── Identity ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc=f"Type of task: {TASK_TYPE_VALUES}",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="queued",
        doc=f"One of: {TASK_STATUS_VALUES}",
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Owner of the task; nullable for system-wide tasks.",
    )

    # ── Payload & Results ───────────────────────────────────────────────────
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Parameters needed to execute the task (no raw secrets).",
    )

    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Structured execution summary on success.",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Safe error message if task failed.",
    )

    # ── Attempts & Retry Scheduling ─────────────────────────────────────────
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        doc="Number of times execution has been attempted.",
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("3"),
        doc="Maximum permitted attempts before terminal failure.",
    )

    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="Timestamp when task becomes eligible for claiming (handles backoff).",
    )

    # ── Worker Leases ───────────────────────────────────────────────────────
    worker_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Identifier of the worker currently executing this task.",
    )

    lease_timeout_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Worker lease expiration timestamp for crash detection.",
    )

    # ── Timestamps ──────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution of current attempt started.",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When task entered terminal state (succeeded, failed, cancelled).",
    )

    # ── Relationships ───────────────────────────────────────────────────────
    user = relationship("User", backref="tasks")

    # ── Indexes ─────────────────────────────────────────────────────────────
    __table_args__ = (
        Index(
            "idx_tasks_claim_eligible",
            "status",
            "available_at",
            postgresql_where=text("status = 'queued'"),
        ),
        Index(
            "idx_tasks_stale_lease",
            "status",
            "lease_timeout_at",
            postgresql_where=text("status = 'running'"),
        ),
        Index("idx_tasks_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Task id={self.id} type={self.task_type!r} status={self.status!r} "
            f"attempts={self.attempt_count}/{self.max_attempts}>"
        )
