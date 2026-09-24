"""add email otps table

Revision ID: a1b2c3d4e5f6
Revises: 9d4e5f6a7b8c
Create Date: 2026-09-24 14:00:00.000000

Architecture changes:
- Creates `email_otps` table for secure, hashed email OTP authentication.
- Tracks hashed OTP, expiry, attempt counts, creation time (cooldown), and consumption time.
- Fully reversible upgrade/downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9d4e5f6a7b8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_otps",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_otp", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_email_otps_email", "email_otps", ["email"], unique=False)
    op.create_index("idx_email_otps_created_at", "email_otps", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_email_otps_created_at", table_name="email_otps")
    op.drop_index("idx_email_otps_email", table_name="email_otps")
    op.drop_table("email_otps")
