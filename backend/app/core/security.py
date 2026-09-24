"""
Security and authentication utilities.

Provides:
  - Password hashing and verification using Argon2id (argon2-cffi)
  - JWT access token generation and decoding using PyJWT
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Initialize Argon2id password hasher with secure defaults
_ph = PasswordHasher()


# ── OTP Generation, Hashing & Verification ───────────────────────────────────

def generate_otp_code() -> str:
    """Generate a cryptographically secure 6-digit numeric OTP."""
    code_int = secrets.randbelow(1_000_000)
    return f"{code_int:06d}"


def hash_otp(otp_code: str) -> str:
    """
    Hash a 6-digit OTP using a unique 16-byte random salt and HMAC-SHA256.

    Format: <salt_hex>$<sha256_hex>
    Plaintext OTP is NEVER stored.
    """
    if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
        raise ValueError("OTP code must be a 6-digit numeric string")
    settings = get_settings()
    salt = secrets.token_hex(16)
    secret_key = settings.JWT_SECRET_KEY
    digest = hashlib.sha256(f"{salt}:{otp_code}:{secret_key}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_otp_hash(plain_otp: str, stored_hash: str) -> bool:
    """
    Verify a candidate plaintext OTP against the stored salted hash in constant time.
    """
    if not plain_otp or not stored_hash or "$" not in stored_hash:
        return False
    try:
        salt, expected_digest = stored_hash.split("$", 1)
        settings = get_settings()
        secret_key = settings.JWT_SECRET_KEY
        computed_digest = hashlib.sha256(f"{salt}:{plain_otp}:{secret_key}".encode("utf-8")).hexdigest()
        return secrets.compare_digest(computed_digest, expected_digest)
    except Exception as exc:
        logger.warning("Error verifying OTP hash: %s", exc)
        return False


# ── Password Hashing & Verification ──────────────────────────────────────────

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using Argon2id.

    Returns the complete hash string (including algorithm, salt, and parameters).
    Plaintext passwords must NEVER be stored or logged.
    """
    if not password:
        raise ValueError("Password must not be empty")
    return _ph.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against a stored Argon2id hash.

    Returns True if the password matches, False otherwise.
    Never raises on verification mismatch or malformed hash format.
    """
    if not plain_password or not password_hash:
        return False
    try:
        return _ph.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as exc:
        logger.warning("Unexpected error during password verification: %s", exc)
        return False


# ── JWT Handling ─────────────────────────────────────────────────────────────

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Generate a JWT access token containing subject claims and expiration time.

    Standard claims:
      - sub: subject / user ID (string)
      - email: user email
      - type: "access"
      - iat: issued-at timestamp
      - exp: expiration timestamp
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = data.copy()
    to_encode.update({
        "iat": now,
        "exp": expire,
        "type": "access",
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Validates signature, expiration, token type ("access"), and UUID subject format.

    Returns the payload dictionary if valid.
    Raises:
      - jwt.ExpiredSignatureError: if the token has expired
      - jwt.InvalidTokenError: if the signature, structure, type, or subject claim is invalid
    """
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise jwt.InvalidTokenError("Missing subject claim")

    try:
        uuid.UUID(str(sub))
    except (ValueError, TypeError, AttributeError):
        raise jwt.InvalidTokenError("Invalid subject UUID format")

    return payload
