"""
tests/test_auth_router.py — HTTP-level integration tests for auth router (/api/auth).

Uses FastAPI TestClient to test real HTTP request/response envelope behavior:
  - POST /api/auth/otp/request → 200 OK
  - POST /api/auth/otp/request with cooldown → 429 RATE_LIMIT_EXCEEDED
  - POST /api/auth/otp/verify with valid OTP → 200 OK and TokenResponse
  - POST /api/auth/otp/verify with invalid OTP → 400 INVALID_OTP
  - POST /api/auth/otp/verify with max attempts → 429 TOO_MANY_ATTEMPTS
  - GET  /api/auth/me with valid token → 200 OK and UserResponse
  - GET  /api/auth/me without token → 401 INVALID_TOKEN
  - GET  /api/auth/me with invalid/expired token → 401 INVALID_TOKEN / TOKEN_EXPIRED
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import create_access_token, hash_otp
from app.models.email_otp import EmailOtp
from app.models.user import User
from app.services.user_service import UserService
from tests.conftest import needs_db


@needs_db
def test_http_otp_request_success(client, db):
    """POST /api/auth/otp/request returns 200 OK and ApiResponse[OtpResponse]."""
    response = client.post(
        "/api/auth/otp/request",
        json={"email": "http_otp@example.com"},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["error"] is None
    data = json_data["data"]
    assert data["email"] == "http_otp@example.com"
    assert "Verification code sent" in data["message"]


@needs_db
def test_http_otp_request_cooldown(client, db):
    """POST /api/auth/otp/request within cooldown returns 429 RATE_LIMIT_EXCEEDED."""
    client.post(
        "/api/auth/otp/request",
        json={"email": "cooldown_router@example.com"},
    )

    response = client.post(
        "/api/auth/otp/request",
        json={"email": "cooldown_router@example.com"},
    )
    assert response.status_code == 429
    json_data = response.json()
    assert json_data["data"] is None
    error = json_data["error"]
    assert error["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Please wait" in error["message"]


@needs_db
def test_http_otp_verify_success(client, db):
    """POST /api/auth/otp/verify returns 200 OK and TokenResponse envelope."""
    email = "verify_router@example.com"
    otp_code = "123456"

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

    response = client.post(
        "/api/auth/otp/verify",
        json={"email": email, "otp": otp_code},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["error"] is None
    data = json_data["data"]
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20


@needs_db
def test_http_otp_verify_invalid_code(client, db):
    """POST /api/auth/otp/verify with incorrect code returns 400 INVALID_OTP."""
    email = "wrong_otp_router@example.com"
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

    response = client.post(
        "/api/auth/otp/verify",
        json={"email": email, "otp": "999999"},
    )
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["data"] is None
    error = json_data["error"]
    assert error["code"] == "INVALID_OTP"
    assert "attempt(s) remaining" in error["message"]


@needs_db
def test_http_otp_verify_max_attempts_exceeded(client, db):
    """POST /api/auth/otp/verify when attempts are exhausted returns 429 TOO_MANY_ATTEMPTS."""
    email = "locked_otp_router@example.com"
    otp_record = EmailOtp(
        id=uuid.uuid4(),
        email=email,
        hashed_otp=hash_otp("111111"),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        attempts=5,
        max_attempts=5,
        created_at=datetime.now(UTC),
        consumed_at=None,
    )
    db.add(otp_record)
    db.commit()

    response = client.post(
        "/api/auth/otp/verify",
        json={"email": email, "otp": "111111"},
    )
    assert response.status_code == 429
    json_data = response.json()
    assert json_data["data"] is None
    error = json_data["error"]
    assert error["code"] == "TOO_MANY_ATTEMPTS"


@needs_db
def test_http_get_me_valid_token(client, db):
    """GET /api/auth/me with valid Bearer token returns 200 OK and UserResponse envelope."""
    user = UserService(db).create_email_user(email="me_endpoint@example.com", name="Me User")
    db.commit()

    token = create_access_token(data={"sub": str(user.id), "email": user.email})

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["error"] is None
    data = json_data["data"]
    assert data["id"] == str(user.id)
    assert data["email"] == "me_endpoint@example.com"
    assert data["name"] == "Me User"


def test_http_get_me_without_token(client):
    """GET /api/auth/me without Authorization header returns 401 INVALID_TOKEN."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    json_data = response.json()
    assert json_data["data"] is None
    assert json_data["error"]["code"] == "INVALID_TOKEN"


def test_http_get_me_invalid_token(client):
    """GET /api/auth/me with invalid signature returns 401 INVALID_TOKEN."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401
    json_data = response.json()
    assert json_data["data"] is None
    assert json_data["error"]["code"] == "INVALID_TOKEN"


@needs_db
def test_http_get_me_expired_token(client, db):
    """GET /api/auth/me with expired token returns 401 TOKEN_EXPIRED."""
    user = UserService(db).create_email_user(email="expired_router@example.com")
    db.commit()

    expired_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(seconds=-60),
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    json_data = response.json()
    assert json_data["data"] is None
    assert json_data["error"]["code"] == "TOKEN_EXPIRED"


def test_http_get_me_invalid_token_type(client):
    """GET /api/auth/me with wrong token 'type' claim returns 401 INVALID_TOKEN."""
    import uuid
    from datetime import datetime, timezone
    import jwt
    from app.config import get_settings

    settings = get_settings()
    now = datetime.now(timezone.utc)
    wrong_type_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "refresh", "iat": now, "exp": now + timedelta(minutes=10)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {wrong_type_token}"},
    )
    assert response.status_code == 401
    json_data = response.json()
    assert json_data["data"] is None
    assert json_data["error"]["code"] == "INVALID_TOKEN"


def test_http_get_me_invalid_uuid_subject(client):
    """GET /api/auth/me with non-UUID 'sub' claim returns 401 INVALID_TOKEN."""
    from datetime import datetime, timezone
    import jwt
    from app.config import get_settings

    settings = get_settings()
    now = datetime.now(timezone.utc)
    malformed_sub_token = jwt.encode(
        {"sub": "invalid-non-uuid-string", "type": "access", "iat": now, "exp": now + timedelta(minutes=10)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {malformed_sub_token}"},
    )
    assert response.status_code == 401
    json_data = response.json()
    assert json_data["data"] is None
    assert json_data["error"]["code"] == "INVALID_TOKEN"
