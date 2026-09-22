"""
Google OAuth 2.0 and OpenID Connect (OIDC) authentication utilities.

Provides:
  - PKCE (Proof Key for Code Exchange) generation and verification
  - CSRF state generation and validation
  - Google authorization URL generation
  - Authorization code exchange via Google token endpoint
  - OIDC ID token validation (issuer, audience, signature, exp, email_verified, sub)
  - Single-use short-lived handoff code store for secure token handoff to frontend
"""

import base64
import hashlib
import logging
import secrets
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, cast
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import get_settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
ALLOWED_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


# ── PKCE & State Helpers ──────────────────────────────────────────────────────

def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge (S256).

    Returns:
        (code_verifier, code_challenge)
    """
    verifier = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(hashed).decode("ascii").rstrip("=")
    return verifier, challenge


def generate_oauth_state() -> str:
    """Generate cryptographically secure random state parameter for CSRF protection."""
    return secrets.token_urlsafe(32)


def build_google_authorization_url(state: str, code_challenge: str) -> str:
    """
    Construct the Google OAuth 2.0 authorization endpoint URL.
    """
    settings = get_settings()
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


# ── Google Token Exchange & Verification ──────────────────────────────────────

def exchange_code_for_google_tokens(code: str, code_verifier: str) -> dict[str, Any]:
    """
    Exchange authorization code for tokens at Google's token endpoint.

    Raises:
        ValueError: if exchange fails or token endpoint returns non-200.
    """
    settings = get_settings()
    payload = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        response = httpx.post(GOOGLE_TOKEN_URL, data=payload, timeout=10.0)
    except Exception as exc:
        logger.error("Failed to connect to Google token endpoint: %s", exc)
        raise ValueError("Failed to connect to Google token endpoint") from exc

    if response.status_code != 200:
        logger.error("Google token exchange error %s: %s", response.status_code, response.text)
        raise ValueError("Failed to exchange code with Google")

    data = cast(dict[str, Any], response.json())
    if "id_token" not in data:
        raise ValueError("Google token response did not include id_token")

    return data


def verify_google_id_token(
    token_str: str,
    client_id: str | None = None,
    request: google_requests.Request | None = None,
) -> dict[str, Any]:
    """
    Verify Google OpenID Connect ID token authenticity and claims.

    Validates:
      - Cryptographic signature against Google's public keys
      - Expiration timestamp
      - Issuer is Google (accounts.google.com or https://accounts.google.com)
      - Audience matches our GOOGLE_CLIENT_ID
      - Email is present and email_verified is True
      - Stable user subject (`sub`) is present

    Returns:
        Verified claims dictionary.

    Raises:
        ValueError: if token is invalid, expired, unverified, or claims are missing.
    """
    settings = get_settings()
    expected_client_id = client_id or settings.GOOGLE_CLIENT_ID
    req = request or google_requests.Request()

    try:
        claims = cast(
            dict[str, Any],
            id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
                token_str,
                req,
                audience=expected_client_id,
                clock_skew_in_seconds=10,
            ),
        )
    except Exception as exc:
        logger.warning("Google ID token verification failed: %s", exc)
        raise ValueError(f"Invalid Google ID token: {exc}") from exc

    iss = claims.get("iss")
    if iss not in ALLOWED_GOOGLE_ISSUERS:
        logger.warning("Invalid Google ID token issuer: %s", iss)
        raise ValueError(f"Invalid issuer '{iss}' in Google ID token")

    if not claims.get("sub"):
        raise ValueError("Google ID token missing 'sub' claim")

    if not claims.get("email"):
        raise ValueError("Google ID token missing 'email' claim")

    if not claims.get("email_verified"):
        raise ValueError("Google account email is not verified")

    return claims


# ── Temporary Handoff Code Store ──────────────────────────────────────────────

class HandoffCodeStore(ABC):
    """Abstract interface for short-lived, single-use handoff codes."""

    @abstractmethod
    def create_code(self, user_id: str, email: str, ttl_seconds: int = 60) -> str:
        """Issue a temporary single-use code for the user."""
        pass

    @abstractmethod
    def consume_code(self, code: str) -> dict[str, str] | None:
        """Retrieve and immediately invalidate the code. Returns None if invalid/expired."""
        pass


class InMemoryHandoffCodeStore(HandoffCodeStore):
    """
    Thread-safe in-memory single-use code store with expiration (TTL).
    Suitable for local development. Can be swapped for Redis in production.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, dict[str, Any]] = {}

    def _purge_expired(self, now: float) -> None:
        expired_keys = [k for k, v in self._store.items() if v["expires_at"] <= now]
        for k in expired_keys:
            del self._store[k]

    def create_code(self, user_id: str, email: str, ttl_seconds: int = 60) -> str:
        code = secrets.token_urlsafe(32)
        now = time.time()
        with self._lock:
            self._purge_expired(now)
            self._store[code] = {
                "user_id": str(user_id),
                "email": email,
                "expires_at": now + ttl_seconds,
            }
        return code

    def consume_code(self, code: str) -> dict[str, str] | None:
        now = time.time()
        with self._lock:
            self._purge_expired(now)
            entry = self._store.pop(code, None)
            if entry is None:
                return None
            if entry["expires_at"] <= now:
                return None
            return {
                "user_id": entry["user_id"],
                "email": entry["email"],
            }


# Default singleton instance for local dev
_default_handoff_store = InMemoryHandoffCodeStore()


def get_handoff_store() -> HandoffCodeStore:
    """Return the active handoff code store instance."""
    return _default_handoff_store
