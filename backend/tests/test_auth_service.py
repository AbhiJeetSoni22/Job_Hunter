"""
tests/test_auth_service.py — Unit and integration tests for authentication foundation.

Covers all 24 required authentication test cases:
  1-7. Registration logic, hashing, validation, duplicates, and plaintext exclusion.
  8-14. Login authentication, password verification, inactive check, JWT issuance, claims.
  15-21. Current user dependency resolution, header parsing, JWT decoding, inactive/missing handling.
  22-24. Security invariants (hash safety, argon2 verification vs plaintext).
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.user_service import (
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    UserService,
)
from tests.conftest import needs_db


# ── 1-7: Registration Tests ──────────────────────────────────────────────────

@needs_db
def test_1_successful_registration(db):
    """1. Successful registration creates User row in DB."""
    service = UserService(db)
    payload = UserRegisterRequest(
        name="Alice Engineer",
        email="Alice@Example.COM",
        password="SecurePassword123!",
    )
    user = service.register_user(payload)

    assert user.id is not None
    assert user.name == "Alice Engineer"
    assert user.email == "alice@example.com"  # Normalized to lowercase
    assert user.is_active is True
    assert user.password_hash != "SecurePassword123!"


@needs_db
def test_2_duplicate_email_registration(db):
    """2. Registering with an existing email raises DuplicateEmailError."""
    service = UserService(db)
    payload1 = UserRegisterRequest(
        name="Bob Smith",
        email="bob@example.com",
        password="Password123!",
    )
    service.register_user(payload1)

    payload2 = UserRegisterRequest(
        name="Bob Duplicate",
        email="BOB@example.com",  # Same email, different case
        password="Password456!",
    )
    with pytest.raises(DuplicateEmailError) as exc_info:
        service.register_user(payload2)

    assert "already exists" in str(exc_info.value)


def test_3_invalid_email_validation():
    """3. Invalid email format raises Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        UserRegisterRequest(
            name="Invalid User",
            email="not-an-email",
            password="Password123!",
        )


def test_4_invalid_or_empty_password_validation():
    """4. Empty or short password raises Pydantic ValidationError or ValueError."""
    with pytest.raises(ValidationError):
        UserRegisterRequest(
            name="Short Pass",
            email="user@example.com",
            password="123",  # < 8 chars
        )

    with pytest.raises(ValueError):
        hash_password("")


def test_5_required_fields_validation():
    """5. Missing required fields raise Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        UserRegisterRequest.model_validate({"email": "test@example.com", "password": "Password123!"})

    with pytest.raises(ValidationError):
        UserRegisterRequest.model_validate({"name": "Test User", "password": "Password123!"})


@needs_db
def test_6_password_stored_as_hash(db):
    """6. Password is stored strictly as an Argon2id hash."""
    service = UserService(db)
    payload = UserRegisterRequest(
        name="Hash Test",
        email="hash@example.com",
        password="MySecretPassword123!",
    )
    user = service.register_user(payload)

    assert user.password_hash.startswith("$argon2")
    assert verify_password("MySecretPassword123!", user.password_hash) is True


@needs_db
def test_7_plaintext_password_never_stored_or_returned(db):
    """7. Plaintext password is never stored or returned by UserResponse."""
    service = UserService(db)
    payload = UserRegisterRequest(
        name="Safety Test",
        email="safety@example.com",
        password="SuperSecretPassword!",
    )
    user = service.register_user(payload)

    response_schema = UserResponse.model_validate(user)
    schema_dict = response_schema.model_dump()

    assert "password" not in schema_dict
    assert "password_hash" not in schema_dict
    assert "SuperSecretPassword!" not in str(user.__dict__)


# ── 8-14: Login Tests ────────────────────────────────────────────────────────

@needs_db
def test_8_successful_login(db):
    """8. Successful login returns User object."""
    service = UserService(db)
    reg_payload = UserRegisterRequest(
        name="Login User",
        email="login@example.com",
        password="CorrectPassword123!",
    )
    service.register_user(reg_payload)

    login_payload = UserLoginRequest(
        email="LOGIN@example.com",  # Case insensitive
        password="CorrectPassword123!",
    )
    user = service.authenticate_user(login_payload)

    assert user.email == "login@example.com"


@needs_db
def test_9_login_wrong_password(db):
    """9. Login with incorrect password raises InvalidCredentialsError."""
    service = UserService(db)
    service.register_user(UserRegisterRequest(
        name="Pass Test",
        email="wrongpass@example.com",
        password="RightPassword123!",
    ))

    with pytest.raises(InvalidCredentialsError):
        service.authenticate_user(UserLoginRequest(
            email="wrongpass@example.com",
            password="WrongPassword123!",
        ))


@needs_db
def test_10_login_unknown_email(db):
    """10. Login with non-existent email raises InvalidCredentialsError."""
    service = UserService(db)
    with pytest.raises(InvalidCredentialsError):
        service.authenticate_user(UserLoginRequest(
            email="nobody@example.com",
            password="Password123!",
        ))


@needs_db
def test_11_login_inactive_user(db):
    """11. Login with an inactive user account raises InactiveUserError."""
    service = UserService(db)
    user = service.register_user(UserRegisterRequest(
        name="Inactive User",
        email="inactive@example.com",
        password="Password123!",
    ))
    user.is_active = False
    db.commit()

    with pytest.raises(InactiveUserError):
        service.authenticate_user(UserLoginRequest(
            email="inactive@example.com",
            password="Password123!",
        ))


def test_12_jwt_generation():
    """12. JWT access token is generated successfully."""
    valid_uuid = str(uuid.uuid4())
    token = create_access_token(data={"sub": valid_uuid, "email": "test@example.com"})
    assert isinstance(token, str)
    assert len(token) > 20


def test_13_jwt_contains_appropriate_claims():
    """13. Generated JWT contains sub, email, iat, exp, and type claims."""
    valid_uuid = str(uuid.uuid4())
    token = create_access_token(data={"sub": valid_uuid, "email": "claim@example.com"})
    payload = decode_access_token(token)

    assert payload["sub"] == valid_uuid
    assert payload["email"] == "claim@example.com"
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload


def test_14_expired_invalid_token_decoding():
    """14. Expired or tampered JWT tokens raise ExpiredSignatureError / InvalidTokenError."""
    # Test expired token
    expired_token = create_access_token(
        data={"sub": str(uuid.uuid4())},
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)

    # Test invalid signature
    tampered_token = expired_token + "tampered"
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered_token)


# ── 15-21: Current User Tests ────────────────────────────────────────────────

@needs_db
def test_15_valid_token_returns_current_user(db):
    """15. get_current_user dependency resolves user for valid token."""
    from app.dependencies import get_current_user
    from fastapi.security import HTTPAuthorizationCredentials

    service = UserService(db)
    user = service.register_user(UserRegisterRequest(
        name="Current User Test",
        email="current@example.com",
        password="Password123!",
    ))

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    resolved_user = get_current_user(db=db, credentials=creds)
    assert resolved_user.id == user.id
    assert resolved_user.email == "current@example.com"


def test_16_missing_authorization_header(db_engine):
    """16. Missing authorization credentials raises 401 INVALID_TOKEN."""
    from app.dependencies import get_current_user
    from fastapi import HTTPException

    mock_db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=mock_db, credentials=None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "INVALID_TOKEN"


def test_17_malformed_bearer_token(db_engine):
    """17. Malformed Bearer token raises 401 INVALID_TOKEN."""
    from app.dependencies import get_current_user
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    mock_db = MagicMock()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=mock_db, credentials=creds)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "INVALID_TOKEN"


def test_18_invalid_jwt_token(db_engine):
    """18. Invalid JWT signature raises 401 INVALID_TOKEN."""
    from app.dependencies import get_current_user
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    mock_db = MagicMock()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.jwt.token")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=mock_db, credentials=creds)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "INVALID_TOKEN"


def test_19_expired_jwt_token(db_engine):
    """19. Expired JWT raises 401 TOKEN_EXPIRED."""
    from app.dependencies import get_current_user
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    expired_token = create_access_token(
        data={"sub": str(uuid.uuid4())},
        expires_delta=timedelta(seconds=-60),
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)
    mock_db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=mock_db, credentials=creds)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "TOKEN_EXPIRED"


@needs_db
def test_20_deleted_nonexistent_user(db):
    """20. Valid JWT for deleted/nonexistent user ID raises 401 USER_NOT_FOUND."""
    from app.dependencies import get_current_user
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    fake_id = str(uuid.uuid4())
    token = create_access_token(data={"sub": fake_id, "email": "deleted@example.com"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=db, credentials=creds)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "USER_NOT_FOUND"


@needs_db
def test_21_inactive_user_token(db):
    """21. Valid JWT for inactive user raises 401 INACTIVE_USER."""
    from app.dependencies import get_current_user
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    service = UserService(db)
    user = service.register_user(UserRegisterRequest(
        name="Deactivated User",
        email="deactive@example.com",
        password="Password123!",
    ))
    user.is_active = False
    db.commit()

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=db, credentials=creds)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "INACTIVE_USER"


# ── 22-24: Security Invariants ───────────────────────────────────────────────

def test_22_password_hash_never_returned_by_api_schema():
    """22. Pydantic UserResponse schema does not define or include password_hash."""
    fields = UserResponse.model_fields.keys()
    assert "password" not in fields
    assert "password_hash" not in fields


def test_23_password_hash_not_equal_to_plaintext():
    """23. Password hash is fundamentally different from plaintext input."""
    plain = "MySecretPass123!"
    hashed = hash_password(plain)
    assert plain != hashed
    assert plain not in hashed


def test_24_cannot_authenticate_using_plaintext_as_stored_hash():
    """24. Passing plaintext password directly as password_hash fails verification."""
    plain = "MySecretPass123!"
    assert verify_password(plain, plain) is False


def test_25_jwt_token_type_validation():
    """25. Token with missing or incorrect 'type' claim raises InvalidTokenError."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    # Missing type claim
    token1 = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": now, "exp": now + timedelta(minutes=10)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token1)

    # Wrong type claim
    token2 = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "refresh", "iat": now, "exp": now + timedelta(minutes=10)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token2)


def test_26_jwt_malformed_subject_uuid_validation():
    """26. Token with malformed non-UUID 'sub' claim raises InvalidTokenError."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {"sub": "not-a-valid-uuid", "type": "access", "iat": now, "exp": now + timedelta(minutes=10)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)

