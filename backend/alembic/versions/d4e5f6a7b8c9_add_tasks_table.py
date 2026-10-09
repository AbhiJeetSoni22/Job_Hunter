"""add tasks table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-09 18:30:00.000000

Architecture changes:
- Creates `tasks` table for PostgreSQL-backed durable task queue and worker processing.
- Supports atomic claiming via SELECT ... FOR UPDATE SKIP LOCKED.
- Supports worker leases, crash recovery, exponential backoff retries, and optional user ownership.
- Fully reversible upgrade/downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=True),
        sa.Column("lease_timeout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tasks_claim_eligible",
        "tasks",
        ["status", "available_at"],
        unique=False,
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index(
        "idx_tasks_stale_lease",
        "tasks",
        ["status", "lease_timeout_at"],
        unique=False,
        postgresql_where=sa.text("status = 'running'"),
    )
    op.create_index(
        "idx_tasks_user_created",
        "tasks",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_tasks_type_status",
        "tasks",
        ["task_type", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_tasks_type_status", table_name="tasks")
    op.drop_index("idx_tasks_user_created", table_name="tasks")
    op.drop_index(
        "idx_tasks_stale_lease",
        table_name="tasks",
        postgresql_where=sa.text("status = 'running'"),
    )
    op.drop_index(
        "idx_tasks_claim_eligible",
        table_name="tasks",
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.drop_table("tasks")
