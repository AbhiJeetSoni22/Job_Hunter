"""add scoring_runs table

Revision ID: 68abbd5b8e5a
Revises: 63d3ec745a23
Create Date: 2026-08-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "68abbd5b8e5a"
down_revision: str | None = "63d3ec745a23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scoring_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="running",
            nullable=False,
        ),
        sa.Column("total_jobs", sa.Integer(), nullable=False),
        sa.Column(
            "scored_jobs", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "failed_jobs", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_scoring_runs_status", "scoring_runs", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_scoring_runs_status", table_name="scoring_runs")
    op.drop_table("scoring_runs")
