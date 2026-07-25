"""add job lifecycle fields

Revision ID: 63d3ec745a23
Revises: cc9c2e74a08d
Create Date: 2026-07-25 15:55:34.282039

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "63d3ec745a23"
down_revision: Union[str, None] = "cc9c2e74a08d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "missing_sync_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_jobs_expired_at", "jobs", ["expired_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_expired_at", table_name="jobs")
    op.drop_column("jobs", "expired_at")
    op.drop_column("jobs", "missing_sync_count")
    op.drop_column("jobs", "last_seen_at")