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
  8. EmailService integration with Gmail SMTP (success, error, dev fallback, security).
"""

import smtplib
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

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


# ── Email Service Integration Tests (Gmail SMTP) ─────────────────────────────

def test_email_service_dev_mode_missing_credentials(monkeypatch, caplog):
    """EmailService in dev mode with missing SMTP password logs OTP and returns True."""
    monkeypatch.setenv("SMTP_PASSWORD", "")
    monkeypatch.setenv("APP_ENV", "development")

    with caplog.at_level("INFO"):
        email_service = EmailService(username="sender@gmail.com", password="", from_email="Job Hunter <sender@gmail.com>")
        result = email_service.send_otp_email("dev_user@example.com", "123456")

    assert result is True
    assert "123456" in caplog.text
    assert "dev_user@example.com" in caplog.text


def test_email_service_prod_mode_missing_credentials(monkeypatch):
    """EmailService in production mode with missing credentials raises EmailDeliveryError."""
    monkeypatch.setenv("SMTP_PASSWORD", "")
    monkeypatch.setenv("APP_ENV", "production")

    email_service = EmailService(username="sender@gmail.com", password="", from_email="Job Hunter <sender@gmail.com>")
    with pytest.raises(EmailDeliveryError) as exc_info:
        email_service.send_otp_email("prod_user@example.com", "123456")

    assert "Email service is not configured" in str(exc_info.value)


def test_email_service_smtp_success(monkeypatch):
    """EmailService establishes STARTTLS, logs in, and dispatches MIME message with OTP."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        email_service = EmailService(
            host="smtp.gmail.com",
            port=587,
            username="sender@gmail.com",
            password="fake-app-password",
            from_email="Job Hunter <sender@gmail.com>",
        )
        success = email_service.send_otp_email("recipient@example.com", "654321")

        assert success is True
        mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=10.0)
        assert mock_server.ehlo.called
        assert mock_server.starttls.called
        mock_server.login.assert_called_once_with("sender@gmail.com", "fake-app-password")
        assert mock_server.send_message.called

        # Verify MIME message content and recipients
        call_args, call_kwargs = mock_server.send_message.call_args
        msg = call_args[0]
        assert call_kwargs["to_addrs"] == ["recipient@example.com"]
        assert call_kwargs["from_addr"] == "sender@gmail.com"
        assert msg["To"] == "recipient@example.com"
        assert msg["From"] == "Job Hunter <sender@gmail.com>"
        assert msg["Subject"] == "654321 is your Job Hunter verification code"

        # Decode MIME payload parts (plain text & HTML)
        payloads = [part.get_payload(decode=True).decode("utf-8") for part in msg.get_payload()]
        assert any("654321" in p for p in payloads)
        assert any("10 minutes" in p for p in payloads)


def test_email_service_smtp_auth_failure(monkeypatch):
    """SMTP authentication failure is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        email_service = EmailService(
            username="sender@gmail.com",
            password="wrong-password",
        )
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("user@example.com", "111222")

        assert "Failed to authenticate" in str(exc_info.value)


def test_email_service_smtp_connection_failure(monkeypatch):
    """SMTP connection failure is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("smtplib.SMTP", side_effect=smtplib.SMTPConnectError(421, "Cannot connect to server")):
        email_service = EmailService(
            username="sender@gmail.com",
            password="some-password",
        )
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("user@example.com", "333444")

        assert "Failed to connect" in str(exc_info.value)


def test_email_service_smtp_recipient_refused(monkeypatch):
    """SMTP recipient refusal is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPRecipientsRefused({"bad@example.com": (550, b"User unknown")})
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        email_service = EmailService(
            username="sender@gmail.com",
            password="valid-password",
        )
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("bad@example.com", "555666")

        assert "rejected" in str(exc_info.value)


def test_email_service_password_never_logged(monkeypatch, caplog):
    """Verify SMTP password or secret credentials are never exposed in log output."""
    monkeypatch.setenv("APP_ENV", "production")
    secret_pass = "super-secret-google-app-password-xyz"

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Bad credentials")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        email_service = EmailService(
            username="sender@gmail.com",
            password=secret_pass,
        )

        with caplog.at_level("DEBUG"), pytest.raises(EmailDeliveryError):
            email_service.send_otp_email("user@example.com", "123456")

        assert secret_pass not in caplog.text
