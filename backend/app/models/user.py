"""
User ORM model.

Maps to the `users` table.

Design decisions:
  - id is PostgreSQL-generated UUID (gen_random_uuid()), consistent with Job, Resume, etc.
  - email is unique and indexed for fast user lookup during auth.
  - password_hash stores ONLY Argon2id/bcrypt hashes; plaintext passwords are never stored.
  - is_active allows future account deactivation/suspension.
  - No subscription/plan/payment fields in Phase 1 (foundation phase).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """
    Represents a registered user account.
    """

    __tablename__ = "users"

    # ── Identity ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        doc="Primary key — PostgreSQL-generated UUID.",
    )

    # ── Credentials & Profile ────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User's full display name.",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        doc="User's unique email address (normalized to lowercase).",
    )

    password_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Argon2id/bcrypt password hash string. Null for Google-only accounts. Plaintext passwords must NEVER be stored.",
    )

    google_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        doc="Google OAuth stable subject identifier ('sub'). Null for email/password-only accounts.",
    )

    # ── Status ───────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        doc="Flag indicating whether account is active. Inactive users cannot authenticate.",
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="Account registration timestamp.",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="Timestamp of last update to user record.",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("idx_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} is_active={self.is_active}>"
