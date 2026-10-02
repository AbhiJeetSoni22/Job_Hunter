"""
tests/test_otp_service.py — Unit and integration tests for OTP authentication service.

Covers:
  1. OTP generation and secure salted hashing (plaintext never stored).
  2. OTP request lifecycle: database persistence, 10-minute expiry, cooldown rate-limiting.
  3. Invalidation of prior active OTPs upon new request.
  4. OTP verification: successful match, consumption, and user provisioning.
  5. OTP verification: existing user lookup and inactive user handling.
  6. Attempt tracking and locking after max failed attempts.
  7. Expiration validation.
  8. EmailService integration with Resend HTTP API (success, error, dev fallback, security).
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from resend.exceptions import ResendError
from sqlalchemy import select

from app.core.security import generate_otp_code, hash_otp, verify_otp_hash
from app.models.email_otp import EmailOtp
from app.models.user import User
from app.services.email_service import EmailDeliveryError, EmailService
from app.services.otp_service import (
    InvalidOtpError,
    OtpRateLimitError,
    OtpService,
    OtpTooManyAttemptsError,
)
from app.services.user_service import InactiveUserError
from tests.conftest import needs_db

# ── Security & Hashing Tests ──────────────────────────────────────────────────

def test_otp_code_generation():
    """generate_otp_code creates 6-digit numeric string."""
    for _ in range(20):
        code = generate_otp_code()
        assert len(code) == 6
        assert code.isdigit()


def test_otp_hashing_and_verification():
    """hash_otp creates unique salted hash; verify_otp_hash validates match."""
    code = "123456"
    stored_hash1 = hash_otp(code)
    stored_hash2 = hash_otp(code)

    assert stored_hash1 != code
    assert stored_hash1 != stored_hash2  # Unique salt per hash
    assert verify_otp_hash("123456", stored_hash1) is True
    assert verify_otp_hash("654321", stored_hash1) is False
    assert verify_otp_hash("12345", stored_hash1) is False


def test_hash_otp_invalid_format():
    """hash_otp rejects non-6-digit inputs."""
    with pytest.raises(ValueError):
        hash_otp("12345")
    with pytest.raises(ValueError):
        hash_otp("abcdef")


# ── OTP Service Request Lifecycle Tests ───────────────────────────────────────

@needs_db
def test_request_otp_success(db):
    """request_otp persists hashed OTP, sets 10m expiry, and normalizes email."""
    mock_email_service = MagicMock(spec=EmailService)
    mock_email_service.send_otp_email.return_value = True

    service = OtpService(db, email_service=mock_email_service)
    otp_record = service.request_otp("TestUser@Example.COM")

    assert otp_record.id is not None
    assert otp_record.email == "testuser@example.com"
    assert otp_record.attempts == 0
    assert otp_record.max_attempts == 5
    assert otp_record.consumed_at is None

    # Check expiry is roughly 10 minutes in the future
    now = datetime.now(UTC)
    expires_at = otp_record.expires_at if otp_record.expires_at.tzinfo else otp_record.expires_at.replace(tzinfo=UTC)
    assert (expires_at - now).total_seconds() > 500

    # Ensure plaintext OTP was sent to email service
    assert mock_email_service.send_otp_email.called
    sent_args = mock_email_service.send_otp_email.call_args[1]
    assert sent_args["to_email"] == "testuser@example.com"
    assert len(sent_args["otp_code"]) == 6


@needs_db
def test_request_otp_cooldown_rate_limiting(db):
    """request_otp within 60 seconds raises OtpRateLimitError."""
    mock_email_service = MagicMock(spec=EmailService)
    mock_email_service.send_otp_email.return_value = True

    service = OtpService(db, email_service=mock_email_service)
    service.request_otp("cooldown@example.com")

    # Second request immediately after
    with pytest.raises(OtpRateLimitError) as exc_info:
        service.request_otp("COOLDOWN@example.com")

    assert "Please wait" in str(exc_info.value)


@needs_db
def test_request_otp_invalidates_prior_otps(db):
    """request_otp marks any prior active OTPs for the same email as consumed/invalidated."""
    mock_email_service = MagicMock(spec=EmailService)
    mock_email_service.send_otp_email.return_value = True

    service = OtpService(db, email_service=mock_email_service)
    otp1 = service.request_otp("repeat@example.com")

    # Manually backdate created_at of otp1 to simulate 65 seconds passed
    otp1.created_at = datetime.now(UTC) - timedelta(seconds=65)
    db.commit()

    otp2 = service.request_otp("repeat@example.com")
    db.refresh(otp1)

    assert otp1.consumed_at is not None
    assert otp2.consumed_at is None
    assert otp1.id != otp2.id


@needs_db
def test_request_otp_email_delivery_failure_rolls_back_db(db):
    """When email delivery fails, request_otp rolls back the session and does not persist OTP."""
    mock_email_service = MagicMock(spec=EmailService)
    mock_email_service.send_otp_email.side_effect = EmailDeliveryError("Failed to deliver")

    service = OtpService(db, email_service=mock_email_service)
    with pytest.raises(EmailDeliveryError):
        service.request_otp("fail_delivery@example.com")

    # Verify no record was persisted
    stmt = select(EmailOtp).where(EmailOtp.email == "fail_delivery@example.com")
    assert db.execute(stmt).scalar_one_or_none() is None


# ── OTP Service Verification Tests ───────────────────────────────────────────

@needs_db
def test_verify_otp_new_user_provisioning(db):
    """verify_otp with correct code consumes OTP and creates new active User."""
    email = "new_otp_user@example.com"
    otp_code = "789123"
    hashed = hash_otp(otp_code)

    otp_record = EmailOtp(
        id=uuid.uuid4(),
        email=email,
        hashed_otp=hashed,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        attempts=0,
        max_attempts=5,
        created_at=datetime.now(UTC),
        consumed_at=None,
    )
    db.add(otp_record)
    db.commit()

    service = OtpService(db)
    user = service.verify_otp(email, otp_code)

    assert user.id is not None
    assert user.email == email
    assert user.name == "New_otp_user"
    assert user.password_hash is None
    assert user.is_active is True

    db.refresh(otp_record)
    assert otp_record.consumed_at is not None


@needs_db
def test_verify_otp_existing_user(db):
    """verify_otp with existing user authenticates without altering user metadata."""
    email = "existing_otp_user@example.com"
    existing_user = User(
        id=uuid.uuid4(),
        name="Existing Jane",
        email=email,
        password_hash=None,
        google_id=None,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(existing_user)

    otp_code = "654321"
    otp_record = EmailOtp(
        id=uuid.uuid4(),
        email=email,
        hashed_otp=hash_otp(otp_code),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        attempts=0,
        max_attempts=5,
        created_at=datetime.now(UTC),
        consumed_at=None,
    )
    db.add(otp_record)
    db.commit()

    service = OtpService(db)
    user = service.verify_otp(email, otp_code)

    assert user.id == existing_user.id
    assert user.name == "Existing Jane"


@needs_db
def test_verify_otp_inactive_user(db):
    """verify_otp for disabled/inactive account raises InactiveUserError."""
    email = "inactive_otp_user@example.com"
    inactive_user = User(
        id=uuid.uuid4(),
        name="Inactive User",
        email=email,
        password_hash=None,
        google_id=None,
        is_active=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(inactive_user)

    otp_code = "112233"
    otp_record = EmailOtp(
        id=uuid.uuid4(),
        email=email,
        hashed_otp=hash_otp(otp_code),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        attempts=0,
        max_attempts=5,
        created_at=datetime.now(UTC),
        consumed_at=None,
    )
    db.add(otp_record)
    db.commit()

    service = OtpService(db)
    with pytest.raises(InactiveUserError):
        service.verify_otp(email, otp_code)


@needs_db
def test_verify_otp_wrong_code_increments_attempts(db):
    """verify_otp with wrong code increments attempt counter and returns remaining attempts."""
    email = "wrong_code@example.com"
    otp_record = EmailOtp(
        id=uuid.uuid4(),
        email=email,
        hashed_otp=hash_otp("111111"),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        attempts=0,
        max_attempts=5,
        created_at=datetime.now(UTC),
        consumed_at=None,
    )
    db.add(otp_record)
    db.commit()

    service = OtpService(db)
    with pytest.raises(InvalidOtpError) as exc_info:
        service.verify_otp(email, "999999")

    assert "4 attempt(s) remaining" in str(exc_info.value)
    db.refresh(otp_record)
    assert otp_record.attempts == 1
    assert otp_record.consumed_at is None


@needs_db
def test_verify_otp_locks_after_max_attempts(db):
    """verify_otp raises OtpTooManyAttemptsError when max_attempts is reached."""
    email = "lockout@example.com"
    otp_record = EmailOtp(
        id=uuid.uuid4(),
        email=email,
        hashed_otp=hash_otp("111111"),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        attempts=4,
        max_attempts=5,
        created_at=datetime.now(UTC),
        consumed_at=None,
    )
    db.add(otp_record)
    db.commit()

    service = OtpService(db)
    with pytest.raises(OtpTooManyAttemptsError):
        service.verify_otp(email, "000000")

    db.refresh(otp_record)
    assert otp_record.attempts == 5

    # Subsequent attempts also raise OtpTooManyAttemptsError
    with pytest.raises(OtpTooManyAttemptsError):
        service.verify_otp(email, "111111")


@needs_db
def test_verify_otp_expired_code(db):
    """verify_otp with expired timestamp raises InvalidOtpError."""
    email = "expired_otp@example.com"
    otp_record = EmailOtp(
        id=uuid.uuid4(),
        email=email,
        hashed_otp=hash_otp("123456"),
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        attempts=0,
        max_attempts=5,
        created_at=datetime.now(UTC) - timedelta(minutes=11),
        consumed_at=None,
    )
    db.add(otp_record)
    db.commit()

    service = OtpService(db)
    with pytest.raises(InvalidOtpError) as exc_info:
        service.verify_otp(email, "123456")

    assert "expired" in str(exc_info.value)


# ── Email Service Integration Tests (Resend HTTP API) ─────────────────────────

def test_email_service_dev_mode_missing_credentials(monkeypatch, caplog):
    """EmailService in dev mode with missing Resend API key logs OTP and returns True."""
    monkeypatch.setenv("RESEND_API_KEY", "")
    monkeypatch.setenv("APP_ENV", "development")

    with caplog.at_level("INFO"):
        email_service = EmailService(api_key="", from_email="Job Hunter <onboarding@resend.dev>")
        result = email_service.send_otp_email("dev_user@example.com", "123456")

    assert result is True
    assert "123456" in caplog.text
    assert "dev_user@example.com" in caplog.text


def test_email_service_prod_mode_missing_credentials(monkeypatch):
    """EmailService in production mode with missing credentials raises EmailDeliveryError."""
    monkeypatch.setenv("RESEND_API_KEY", "")
    monkeypatch.setenv("APP_ENV", "production")

    email_service = EmailService(api_key="", from_email="Job Hunter <onboarding@resend.dev>")
    with pytest.raises(EmailDeliveryError) as exc_info:
        email_service.send_otp_email("prod_user@example.com", "123456")

    assert "Email service is not configured" in str(exc_info.value)


def test_email_service_resend_success(monkeypatch):
    """EmailService dispatches email via Resend API with expected payload."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("resend.Emails.send") as mock_send:
        mock_send.return_value = {"id": "resend_msg_12345"}

        email_service = EmailService(
            api_key="re_valid_api_key_12345",
            from_email="Job Hunter <noreply@example.com>",
        )
        success = email_service.send_otp_email("recipient@example.com", "654321")

        assert success is True
        mock_send.assert_called_once()
        call_params = mock_send.call_args[0][0]
        assert call_params["from"] == "Job Hunter <noreply@example.com>"
        assert call_params["to"] == ["recipient@example.com"]
        assert call_params["subject"] == "654321 is your Job Hunter verification code"
        assert "654321" in call_params["text"]
        assert "10 minutes" in call_params["text"]
        assert "654321" in call_params["html"]


def test_email_service_resend_api_failure(monkeypatch):
    """Resend API failure (e.g. 401 Invalid API Key) is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("resend.Emails.send") as mock_send:
        mock_send.side_effect = ResendError(
            code=401,
            error_type="invalid_api_key",
            message="API key is invalid",
            suggested_action="Check your API key",
        )

        email_service = EmailService(
            api_key="re_invalid_api_key",
            from_email="Job Hunter <onboarding@resend.dev>",
        )
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("user@example.com", "111222")

        assert "Failed to deliver" in str(exc_info.value)


def test_email_service_resend_rate_limit_failure(monkeypatch):
    """Resend rate limit failure (429) is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("resend.Emails.send") as mock_send:
        mock_send.side_effect = ResendError(
            code=429,
            error_type="rate_limit_exceeded",
            message="Too many requests",
            suggested_action="Please slow down your requests",
        )

        email_service = EmailService(
            api_key="re_test_key",
            from_email="Job Hunter <onboarding@resend.dev>",
        )
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("user@example.com", "222333")

        assert "Failed to deliver" in str(exc_info.value)


def test_email_service_resend_unexpected_exception(monkeypatch):
    """Unexpected network error is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("resend.Emails.send", side_effect=ConnectionError("Connection aborted")):
        email_service = EmailService(
            api_key="re_test_key",
            from_email="Job Hunter <onboarding@resend.dev>",
        )
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("user@example.com", "333444")

        assert "unexpected error occurred" in str(exc_info.value)


def test_email_service_credentials_and_otp_never_logged(monkeypatch, caplog):
    """Verify Resend API key and plain OTP code are never exposed in log output."""
    monkeypatch.setenv("APP_ENV", "production")
    secret_key = "re_super_secret_resend_api_key_xyz987"

    with patch("resend.Emails.send") as mock_send:
        mock_send.side_effect = ResendError(
            code=401,
            error_type="unauthorized",
            message="Authentication failed",
            suggested_action="Check API key",
        )

        email_service = EmailService(
            api_key=secret_key,
            from_email="Job Hunter <onboarding@resend.dev>",
        )

        with caplog.at_level("DEBUG"), pytest.raises(EmailDeliveryError):
            email_service.send_otp_email("sensitive_user@example.com", "987654")

        assert secret_key not in caplog.text
        assert "987654" not in caplog.text
        # Recipient email should be masked
        assert "s***r@example.com" in caplog.text
        assert "sensitive_user@example.com" not in caplog.text
