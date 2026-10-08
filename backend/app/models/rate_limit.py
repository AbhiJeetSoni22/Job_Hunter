"""
RateLimitEvent ORM model.

Maps to the `rate_limit_events` table.
Tracks per-user rate limit events and execution cooldowns for:
  - Expensive AI operations (sliding window rate limit per minute)
  - Scraper runs (concurrency lock and cooldown period)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RateLimitEvent(Base):
    """Log entry for a rate-limited or cooldown-monitored user action."""

    __tablename__ = "rate_limit_events"

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
        index=True,
        doc="User who initiated this action.",
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type of operation, e.g. 'ai_operation' or 'scraper_run'.",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'completed'"),
        doc="Status of operation: 'in_progress', 'completed', or 'failed'.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="Timestamp when the operation was initiated.",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when the operation finished (for cooldown calculation).",
    )

    __table_args__ = (
        Index("idx_rate_limit_user_event_created", "user_id", "event_type", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<RateLimitEvent id={self.id} user_id={self.user_id} "
            f"event_type={self.event_type!r} status={self.status!r} "
            f"created_at={self.created_at}>"
        )
