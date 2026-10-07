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

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

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

def test_otp_code_generation() -> None:
    """generate_otp_code creates 6-digit numeric string."""
    for _ in range(20):
        code = generate_otp_code()
        assert len(code) == 6
        assert code.isdigit()


def test_otp_hashing_and_verification() -> None:
    """hash_otp creates unique salted hash; verify_otp_hash validates match."""
    code = "123456"
    stored_hash1 = hash_otp(code)
    stored_hash2 = hash_otp(code)

    assert stored_hash1 != code
    assert stored_hash1 != stored_hash2  # Unique salt per hash
    assert verify_otp_hash("123456", stored_hash1) is True
    assert verify_otp_hash("654321", stored_hash1) is False
    assert verify_otp_hash("12345", stored_hash1) is False


def test_hash_otp_invalid_format() -> None:
    """hash_otp rejects non-6-digit inputs."""
    with pytest.raises(ValueError):
        hash_otp("12345")
    with pytest.raises(ValueError):
        hash_otp("abcdef")


# ── OTP Service Request Lifecycle Tests ───────────────────────────────────────

@needs_db
def test_request_otp_success(db: Session) -> None:
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
def test_request_otp_cooldown_rate_limiting(db: Session) -> None:
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
def test_request_otp_invalidates_prior_otps(db: Session) -> None:
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
def test_request_otp_email_delivery_failure_rolls_back_db(db: Session) -> None:
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
def test_verify_otp_new_user_provisioning(db: Session) -> None:
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
def test_verify_otp_existing_user(db: Session) -> None:
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
def test_verify_otp_inactive_user(db: Session) -> None:
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
def test_verify_otp_wrong_code_increments_attempts(db: Session) -> None:
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
def test_verify_otp_locks_after_max_attempts(db: Session) -> None:
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
def test_verify_otp_expired_code(db: Session) -> None:
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


# ── Email Service Integration Tests (Brevo API) ─────────────────────────────

def test_email_service_dev_mode_missing_credentials(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """EmailService in dev mode with missing API key logs OTP and returns True."""
    monkeypatch.setenv("BREVO_API_KEY", "")
    monkeypatch.setenv("APP_ENV", "development")

    with caplog.at_level("INFO"):
        email_service = EmailService(api_key="", from_email="sender@example.com")
        result = email_service.send_otp_email("dev_user@example.com", "123456")

    assert result is True
    assert "123456" in caplog.text
    assert "dev_user@example.com" in caplog.text


def test_email_service_prod_mode_missing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """EmailService in production mode with missing credentials raises EmailDeliveryError."""
    monkeypatch.setenv("BREVO_API_KEY", "")
    monkeypatch.setenv("APP_ENV", "production")

    email_service = EmailService(api_key="", from_email="sender@example.com")
    with pytest.raises(EmailDeliveryError) as exc_info:
        email_service.send_otp_email("prod_user@example.com", "123456")

    assert "Email service is not configured" in str(exc_info.value)


def test_email_service_brevo_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """EmailService establishes HTTP connection, authenticates, and dispatches message via Brevo."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("httpx.Client") as mock_httpx_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_client.post.return_value = mock_response
        mock_httpx_cls.return_value = mock_client

        email_service = EmailService(
            api_key="valid-brevo-key",
            from_email="sender@example.com",
            from_name="Job Hunter",
        )
        success = email_service.send_otp_email("recipient@example.com", "654321")

        assert success is True
        assert mock_client.post.called

        # Verify request parameters
        call_args: Any
        call_kwargs: Any
        call_args, call_kwargs = mock_client.post.call_args
        
        assert call_args[0] == "https://api.brevo.com/v3/smtp/email"
        assert call_kwargs["headers"]["api-key"] == "valid-brevo-key"
        
        payload = call_kwargs["json"]
        assert payload["to"][0]["email"] == "recipient@example.com"
        assert payload["sender"]["email"] == "sender@example.com"
        assert payload["sender"]["name"] == "Job Hunter"
        assert payload["subject"] == "654321 is your Job Hunter verification code"
        assert "654321" in payload["textContent"]
        assert "654321" in payload["htmlContent"]
        assert "10 minutes" in payload["textContent"]


def test_email_service_brevo_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brevo 401 authentication failure is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("httpx.Client") as mock_httpx_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"message":"Key not found"}'
        
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )
        mock_httpx_cls.return_value = mock_client

        email_service = EmailService(api_key="wrong-key")
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("user@example.com", "111222")

        assert "Failed to authenticate" in str(exc_info.value)


def test_email_service_brevo_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brevo HTTP connection failure is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("httpx.Client") as mock_httpx_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = httpx.ConnectError("Cannot connect to server")
        mock_httpx_cls.return_value = mock_client

        email_service = EmailService(api_key="some-key")
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("user@example.com", "333444")

        assert "Failed to connect" in str(exc_info.value)


def test_email_service_brevo_timeout_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brevo HTTP timeout is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("httpx.Client") as mock_httpx_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")
        mock_httpx_cls.return_value = mock_client

        email_service = EmailService(api_key="some-key")
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("user@example.com", "333444")

        assert "Failed to connect" in str(exc_info.value)


def test_email_service_brevo_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brevo HTTP 500 failure is converted into EmailDeliveryError."""
    monkeypatch.setenv("APP_ENV", "production")

    with patch("httpx.Client") as mock_httpx_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        mock_httpx_cls.return_value = mock_client

        email_service = EmailService(api_key="valid-key")
        with pytest.raises(EmailDeliveryError) as exc_info:
            email_service.send_otp_email("bad@example.com", "555666")

        assert "Failed to dispatch" in str(exc_info.value)


def test_email_service_api_key_never_logged(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Verify Brevo API key is never exposed in log output."""
    monkeypatch.setenv("APP_ENV", "production")
    secret_key = "super-secret-brevo-api-key-xyz"

    with patch("httpx.Client") as mock_httpx_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )
        mock_httpx_cls.return_value = mock_client

        email_service = EmailService(api_key=secret_key)

        with caplog.at_level("DEBUG"), pytest.raises(EmailDeliveryError):
            email_service.send_otp_email("user@example.com", "123456")

        assert secret_key not in caplog.text
        assert "123456" not in caplog.text
