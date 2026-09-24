"""
OTP authentication service.

Business logic for:
  - OTP generation, secure salted hashing, rate-limiting (cooldown), and dispatch via Resend
  - OTP attempt tracking, expiration validation, consumption, and user provisioning
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import generate_otp_code, hash_otp, verify_otp_hash
from app.models.email_otp import EmailOtp
from app.models.user import User
from app.services.email_service import EmailDeliveryError, EmailService
from app.services.user_service import InactiveUserError, UserService

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 10
OTP_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5


# ── Domain Exceptions ─────────────────────────────────────────────────────────

class OtpError(Exception):
    """Base exception for OTP service errors."""
    pass


class OtpRateLimitError(OtpError):
    """Raised when an OTP request is made within the cooldown period."""
    pass


class InvalidOtpError(OtpError):
    """Raised when an invalid or expired OTP code is submitted."""
    pass


class OtpTooManyAttemptsError(OtpError):
    """Raised when maximum verification attempts for an OTP are exceeded."""
    pass


# ── Service ───────────────────────────────────────────────────────────────────

class OtpService:
    """Service layer managing email OTP lifecycle and verification."""

    def __init__(self, db: Session, email_service: EmailService | None = None) -> None:
        self._db = db
        self._email_service = email_service or EmailService()

    def request_otp(self, email: str) -> EmailOtp:
        """
        Request a 6-digit verification code sent to the given email address.

        Enforces:
          - Email normalization to lowercase.
          - 60-second cooldown rate limit per email.
          - Invalidation of previous unconsumed active OTPs for the same email.
          - Cryptographic salted hashing (plaintext never persisted).
          - 10-minute expiry window.
          - Delivery via Resend transactional email.

        Raises:
            OtpRateLimitError: if called within cooldown period.
            EmailDeliveryError: if email dispatch fails.
        """
        normalized_email = email.strip().lower()
        now = datetime.now(UTC)

        # 1. Rate Limit Cooldown Check
        recent_otp_stmt = (
            select(EmailOtp)
            .where(EmailOtp.email == normalized_email)
            .order_by(EmailOtp.created_at.desc())
            .limit(1)
        )
        recent_otp = self._db.execute(recent_otp_stmt).scalar_one_or_none()
        if recent_otp is not None:
            # Ensure naive datetimes are treated as UTC if needed
            created_at = recent_otp.created_at if recent_otp.created_at.tzinfo else recent_otp.created_at.replace(tzinfo=UTC)
            elapsed_seconds = (now - created_at).total_seconds()
            if elapsed_seconds < OTP_COOLDOWN_SECONDS:
                remaining_wait = int(OTP_COOLDOWN_SECONDS - elapsed_seconds)
                logger.info("OTP rate limited for %s (%s seconds remaining)", normalized_email, remaining_wait)
                raise OtpRateLimitError(
                    f"Please wait {remaining_wait} second(s) before requesting another code."
                )

        # 2. Invalidate older unconsumed OTPs for this email
        old_otps_stmt = (
            select(EmailOtp)
            .where(
                EmailOtp.email == normalized_email,
                EmailOtp.consumed_at.is_(None),
            )
        )
        for old_otp in self._db.execute(old_otps_stmt).scalars():
            old_otp.consumed_at = now

        # 3. Generate and Hash OTP
        otp_code = generate_otp_code()
        hashed_otp = hash_otp(otp_code)
        expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)

        otp_record = EmailOtp(
            id=uuid.uuid4(),
            email=normalized_email,
            hashed_otp=hashed_otp,
            expires_at=expires_at,
            attempts=0,
            max_attempts=OTP_MAX_ATTEMPTS,
            created_at=now,
            consumed_at=None,
        )
        self._db.add(otp_record)
        self._db.flush()

        # 4. Dispatch Email via Resend
        try:
            self._email_service.send_otp_email(to_email=normalized_email, otp_code=otp_code)
        except EmailDeliveryError:
            self._db.rollback()
            raise

        self._db.commit()
        self._db.refresh(otp_record)
        logger.info("Successfully generated and dispatched OTP for %s", normalized_email)
        return otp_record

    def verify_otp(self, email: str, plain_otp: str) -> User:
        """
        Verify the submitted 6-digit OTP code against the active record.

        Enforces:
          - Active, unconsumed record check.
          - Expiration validation.
          - Attempt tracking and locking after max attempts.
          - Constant-time hash comparison.
          - Provisioning or linking user account upon success.

        Raises:
            InvalidOtpError: if OTP is invalid, expired, or incorrect.
            OtpTooManyAttemptsError: if max attempts exceeded.
            InactiveUserError: if resolved user account is inactive.
        """
        normalized_email = email.strip().lower()
        now = datetime.now(UTC)

        # 1. Fetch latest active unconsumed OTP
        stmt = (
            select(EmailOtp)
            .where(
                EmailOtp.email == normalized_email,
                EmailOtp.consumed_at.is_(None),
            )
            .order_by(EmailOtp.created_at.desc())
            .limit(1)
        )
        otp_record = self._db.execute(stmt).scalar_one_or_none()

        if otp_record is None:
            logger.info("OTP verification failed: no active OTP record for %s", normalized_email)
            raise InvalidOtpError("Verification code not found or expired. Please request a new code.")

        expires_at = otp_record.expires_at if otp_record.expires_at.tzinfo else otp_record.expires_at.replace(tzinfo=UTC)
        if now > expires_at:
            logger.info("OTP verification failed: code expired for %s", normalized_email)
            raise InvalidOtpError("Verification code has expired. Please request a new code.")

        if otp_record.attempts >= otp_record.max_attempts:
            logger.warning("OTP verification locked: max attempts exceeded for %s", normalized_email)
            raise OtpTooManyAttemptsError("Too many failed attempts. Please request a new verification code.")

        # 2. Verify Hash
        is_valid = verify_otp_hash(plain_otp, otp_record.hashed_otp)
        if not is_valid:
            otp_record.attempts += 1
            self._db.commit()
            remaining = max(0, otp_record.max_attempts - otp_record.attempts)
            logger.info("OTP verification failed for %s: %s attempts remaining", normalized_email, remaining)
            if remaining == 0:
                raise OtpTooManyAttemptsError("Too many failed attempts. Please request a new verification code.")
            raise InvalidOtpError(f"Invalid verification code. {remaining} attempt(s) remaining.")

        # 3. Mark Consumed
        otp_record.consumed_at = now

        # 4. Resolve or Provision User
        user_service = UserService(self._db)
        existing_user = user_service.get_by_email(normalized_email)

        if existing_user is not None:
            if not existing_user.is_active:
                self._db.commit()
                raise InactiveUserError("User account is inactive.")
            user = existing_user
        else:
            user = user_service.create_email_user(email=normalized_email)

        self._db.commit()
        self._db.refresh(user)
        logger.info("Successfully verified OTP and authenticated user id=%s for email=%s", user.id, normalized_email)
        return user
