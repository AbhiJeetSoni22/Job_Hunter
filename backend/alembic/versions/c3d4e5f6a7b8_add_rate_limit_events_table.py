"""add rate_limit_events table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-08 14:00:00.000000

Architecture changes:
- Creates `rate_limit_events` table for PostgreSQL-backed per-user AI rate limiting
  and scraper cooldown / concurrency locking.
- Tracks user_id, event_type, status, created_at, and completed_at.
- Fully reversible upgrade/downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'completed'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_rate_limit_events_user_id", "rate_limit_events", ["user_id"], unique=False)
    op.create_index("idx_rate_limit_events_created_at", "rate_limit_events", ["created_at"], unique=False)
    op.create_index(
        "idx_rate_limit_user_event_created",
        "rate_limit_events",
        ["user_id", "event_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_rate_limit_user_event_created", table_name="rate_limit_events")
    op.drop_index("idx_rate_limit_events_created_at", table_name="rate_limit_events")
    op.drop_index("idx_rate_limit_events_user_id", table_name="rate_limit_events")
    op.drop_table("rate_limit_events")
