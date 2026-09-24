"""
Email OTP ORM model.

Maps to the `email_otps` table.

Design decisions:
  - id: PostgreSQL-generated UUID.
  - email: normalized lowercase email address, indexed for fast lookup.
  - hashed_otp: secure hash of the 6-digit OTP (plaintext is NEVER stored).
  - expires_at: timestamp when OTP expires (10 minutes from creation).
  - attempts: count of failed verification attempts.
  - max_attempts: limit on attempts before the OTP is invalidated.
  - created_at: creation timestamp (used for rate-limiting / cooldown checks).
  - consumed_at: timestamp when the OTP was successfully verified (or None if pending).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailOtp(Base):
    """
    Represents a temporary, hashed email one-time password (OTP) verification record.
    """

    __tablename__ = "email_otps"

    # ── Identity ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        doc="Primary key — PostgreSQL-generated UUID.",
    )

    # ── OTP Data ────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Normalized lowercase email address.",
    )

    hashed_otp: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Secure cryptographic hash of the 6-digit OTP. Plaintext OTP is NEVER stored.",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Timestamp after which this OTP is considered expired.",
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        doc="Number of failed verification attempts for this OTP code.",
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("5"),
        doc="Maximum number of failed attempts allowed before this OTP is permanently invalidated.",
    )

    # ── Lifecycle Timestamps ────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        doc="Timestamp when this OTP was requested.",
    )

    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when this OTP was successfully verified and consumed. None if pending.",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("idx_email_otps_email", "email"),
        Index("idx_email_otps_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<EmailOtp id={self.id} email={self.email!r} attempts={self.attempts} consumed={self.consumed_at is not None}>"
