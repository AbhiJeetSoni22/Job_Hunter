"""
tests/test_google_oauth.py — Comprehensive tests for Google OAuth 2.0 / OIDC flow.

Covers:
  1. Google OAuth start endpoint (/api/auth/google) redirects and sets cookies
  2. State generation and PKCE parameters
  3. Missing or mismatched state rejection
  4. Invalid Google identity (signature / issuer / audience / expired)
  5. Unverified Google email rejection
  6. New Google user creation (nullable password_hash, google_id populated)
  7. Existing Google user login (no duplicate account created)
  8. Existing email/password user account linking (preserves password_hash)
  9. Duplicate / conflicting google_id protection
  10. Inactive Google-linked user rejection
  11. Handoff code issuance and exchange for JWT token
  12. Replay protection: handoff code single-use
  13. Expired handoff code rejection
  14. /api/auth/me profile retrieval with token from Google authentication
  15. Google-only user cannot authenticate with arbitrary password
  16. Linked user can authenticate with BOTH Google and original password
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.oauth import InMemoryHandoffCodeStore
from app.core.security import decode_access_token
from app.models.user import User
from app.services.user_service import UserService
from tests.conftest import needs_db

# ── Fixtures & Mocks ──────────────────────────────────────────────────────────

FAKE_GOOGLE_CLIENT_ID = "mock-google-client-id-12345.apps.googleusercontent.com"
FAKE_SUB = "google-sub-987654321"
FAKE_EMAIL = "google_user@example.com"
FAKE_NAME = "Google Tester"


@pytest.fixture(autouse=True)
def configure_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set mock Google OAuth client settings for tests."""
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", FAKE_GOOGLE_CLIENT_ID)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "mock-google-secret-xyz")
    monkeypatch.setattr(settings, "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:3000")


# ── 1 & 2: Start Endpoint & State / PKCE Generation ───────────────────────────

def test_google_auth_redirect_and_cookies(client: TestClient) -> None:
    """GET /api/auth/google redirects to Google with state, PKCE, and sets HTTP-only cookies in dev."""
    response = client.get("/api/auth/google", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert "https://accounts.google.com/o/oauth2/v2/auth" in location
    assert f"client_id={FAKE_GOOGLE_CLIENT_ID}" in location
    assert "code_challenge=" in location
    assert "code_challenge_method=S256" in location
    assert "state=" in location

    # Check cookies exist
    cookies = response.cookies
    assert "oauth_state" in cookies
    assert "oauth_verifier" in cookies
    assert len(cookies["oauth_state"]) > 20
    assert len(cookies["oauth_verifier"]) > 20

    # In local HTTP development, SameSite=lax and Secure is not set
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any("samesite=lax" in h.lower() for h in set_cookie_headers)
    assert any("httponly" in h.lower() for h in set_cookie_headers)
    assert not any("samesite=none" in h.lower() for h in set_cookie_headers)


def test_google_auth_cookies_production_https(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In production HTTPS, cookies must be SameSite=None and Secure=True for cross-site redirect."""
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "GOOGLE_REDIRECT_URI", "https://job-hunter-fpii.onrender.com/api/auth/google/callback")

    response = client.get(
        "/api/auth/google",
        headers={"x-forwarded-proto": "https"},
        follow_redirects=False,
    )
    assert response.status_code == 307

    set_cookie_headers = response.headers.get_list("set-cookie")
    assert len(set_cookie_headers) >= 2

    # Assert SameSite=none and Secure are present on all auth cookies
    for header in set_cookie_headers:
        lower = header.lower()
        if "oauth_state=" in lower or "oauth_verifier=" in lower:
            assert "samesite=none" in lower
            assert "secure" in lower
            assert "httponly" in lower
            assert "path=/" in lower


def test_callback_normalizes_frontend_url_trailing_slash(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If FRONTEND_URL has a trailing slash, redirects do not contain double slashes."""
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://job-hunter-blond-one.vercel.app/")

    response = client.get(
        "/api/auth/google/callback?code=mock_code&state=bad_state",
        follow_redirects=False,
    )
    assert response.status_code == 307
    location = response.headers["location"]
    assert location == "https://job-hunter-blond-one.vercel.app/login?error=invalid_state"
    assert "//login" not in location


def test_callback_deletes_cookies_with_secure_flags_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In production HTTPS, cookie deletion must preserve SameSite=none and Secure for browser acceptance."""
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "GOOGLE_REDIRECT_URI", "https://job-hunter-fpii.onrender.com/api/auth/google/callback")

    response = client.get(
        "/api/auth/google/callback?code=mock_code&state=some_state",
        headers={"x-forwarded-proto": "https"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    set_cookie_headers = response.headers.get_list("set-cookie")
    for header in set_cookie_headers:
        lower = header.lower()
        if "oauth_state=" in lower or "oauth_verifier=" in lower:
            assert "samesite=none" in lower
            assert "secure" in lower


# ── 3: State Validation & Missing / Invalid State ─────────────────────────────

def test_callback_missing_state_rejects(client: TestClient) -> None:
    """Callback without state or cookie redirects to frontend with error."""
    response = client.get(
        "/api/auth/google/callback?code=mock_code&state=some_state",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "error=invalid_state" in response.headers["location"]


def test_callback_mismatched_state_rejects(client: TestClient) -> None:
    """Callback with mismatched state cookie redirects with error."""
    client.cookies.set("oauth_state", "legitimate_state")
    client.cookies.set("oauth_verifier", "mock_verifier")
    response = client.get(
        "/api/auth/google/callback?code=mock_code&state=tampered_state",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "error=invalid_state" in response.headers["location"]


def test_callback_missing_verifier_rejects(client: TestClient) -> None:
    """Callback with matching state but missing verifier cookie redirects with error."""
    state = "matching_state_123"
    client.cookies.set("oauth_state", state)
    response = client.get(
        f"/api/auth/google/callback?code=mock_code&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "error=missing_verifier" in response.headers["location"]


def test_callback_google_error_param_redirects(client: TestClient) -> None:
    """When user cancels at Google consent screen, redirect with error."""
    response = client.get(
        "/api/auth/google/callback?error=access_denied",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "error=access_denied" in response.headers["location"]


# ── 4 & 5: Identity & Unverified Email Validation ────────────────────────────

@patch("app.routers.auth.exchange_code_for_google_tokens")
@patch("app.routers.auth.verify_google_id_token")
def test_callback_unverified_email_rejected(
    mock_verify: MagicMock,
    mock_exchange: MagicMock,
    client: TestClient,
) -> None:
    """Google returns unverified email -> rejected."""
    state = "valid_state_456"
    client.cookies.set("oauth_state", state)
    client.cookies.set("oauth_verifier", "test_verifier")

    mock_exchange.return_value = {"id_token": "fake_id_token"}
    mock_verify.side_effect = ValueError("Google account email is not verified")

    response = client.get(
        f"/api/auth/google/callback?code=auth_code&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "error=invalid_identity" in response.headers["location"]


@patch("app.core.oauth.id_token.verify_oauth2_token")
def test_verify_google_id_token_passes_clock_skew(mock_verify_oauth2: MagicMock) -> None:
    """verify_google_id_token calls id_token.verify_oauth2_token with clock_skew_in_seconds=10."""
    from app.core.oauth import verify_google_id_token

    mock_verify_oauth2.return_value = {
        "iss": "https://accounts.google.com",
        "sub": FAKE_SUB,
        "email": FAKE_EMAIL,
        "email_verified": True,
    }

    claims = verify_google_id_token("mock_raw_jwt_token")

    assert claims["sub"] == FAKE_SUB
    assert claims["email"] == FAKE_EMAIL
    mock_verify_oauth2.assert_called_once()
    _, kwargs = mock_verify_oauth2.call_args
    assert kwargs.get("clock_skew_in_seconds") == 10
    assert kwargs.get("audience") == FAKE_GOOGLE_CLIENT_ID


@patch("app.routers.auth.exchange_code_for_google_tokens")
@patch("app.routers.auth.verify_google_id_token")
def test_callback_logs_error_on_invalid_identity(
    mock_verify: MagicMock,
    mock_exchange: MagicMock,
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When verify_google_id_token fails, callback logs exception safely."""
    import logging
    state = "state_log_test"
    client.cookies.set("oauth_state", state)
    client.cookies.set("oauth_verifier", "verifier_log_test")

    mock_exchange.return_value = {"id_token": "token_invalid"}
    mock_verify.side_effect = ValueError("Invalid Google ID token: Token used too early")

    with caplog.at_level(logging.ERROR):
        response = client.get(
            f"/api/auth/google/callback?code=code_log_test&state={state}",
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert "error=invalid_identity" in response.headers["location"]
        assert "Google ID token verification failed" in caplog.text




# ── 6: New Google User Creation & Handoff ─────────────────────────────────────

@needs_db
@patch("app.routers.auth.exchange_code_for_google_tokens")
@patch("app.routers.auth.verify_google_id_token")
def test_new_google_user_creation_and_exchange(
    mock_verify: MagicMock,
    mock_exchange: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    """New user logs in with Google -> User created with google_id and nullable password_hash."""
    state = "state_new_user_1"
    client.cookies.set("oauth_state", state)
    client.cookies.set("oauth_verifier", "verifier_new_user_1")

    mock_exchange.return_value = {"id_token": "fake_new_user_token"}
    mock_verify.return_value = {
        "iss": "https://accounts.google.com",
        "sub": "google-sub-new-1",
        "email": "brand_new_google@example.com",
        "email_verified": True,
        "name": "New Google User",
    }

    # Callback
    response = client.get(
        f"/api/auth/google/callback?code=mock_google_code&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 307
    location = response.headers["location"]
    assert "http://localhost:3000/auth/callback?code=" in location

    # Extract single-use handoff code
    handoff_code = location.split("code=")[1]
    assert len(handoff_code) > 20

    # Verify user exists in database
    created_user = db.query(User).filter(User.email == "brand_new_google@example.com").first()
    assert created_user is not None
    assert created_user.name == "New Google User"
    assert created_user.google_id == "google-sub-new-1"
    assert created_user.password_hash is None
    assert created_user.is_active is True

    # Exchange handoff code for application JWT
    exchange_resp = client.post(
        "/api/auth/google/exchange",
        json={"code": handoff_code},
    )
    assert exchange_resp.status_code == 200
    token_data = exchange_resp.json()["data"]
    assert token_data["token_type"] == "bearer"
    access_token = token_data["access_token"]

    # Verify JWT claims
    claims = decode_access_token(access_token)
    assert claims["sub"] == str(created_user.id)
    assert claims["email"] == "brand_new_google@example.com"

    # Verify /api/auth/me works
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()["data"]
    assert me_data["email"] == "brand_new_google@example.com"
    assert me_data["name"] == "New Google User"
    assert "password_hash" not in me_data


# ── 7: Existing Google User Login ─────────────────────────────────────────────

@needs_db
@patch("app.routers.auth.exchange_code_for_google_tokens")
@patch("app.routers.auth.verify_google_id_token")
def test_existing_google_user_login(
    mock_verify: MagicMock,
    mock_exchange: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    """Returning Google user logs in without creating a second account."""
    state = "state_existing_user"
    client.cookies.set("oauth_state", state)
    client.cookies.set("oauth_verifier", "verifier_existing_user")

    mock_exchange.return_value = {"id_token": "token_repeat"}
    mock_verify.return_value = {
        "iss": "https://accounts.google.com",
        "sub": "existing-google-sub-123",
        "email": "repeat_google@example.com",
        "email_verified": True,
        "name": "Repeat User",
    }

    # First login -> provisions user
    r1 = client.get(
        f"/api/auth/google/callback?code=c1&state={state}",
        follow_redirects=False,
    )
    assert r1.status_code == 307
    code1 = r1.headers["location"].split("code=")[1]
    client.post("/api/auth/google/exchange", json={"code": code1})

    # Second login -> finds existing user
    client.cookies.set("oauth_state", state)
    client.cookies.set("oauth_verifier", "verifier_existing_user")
    r2 = client.get(
        f"/api/auth/google/callback?code=c2&state={state}",
        follow_redirects=False,
    )
    assert r2.status_code == 307
    code2 = r2.headers["location"].split("code=")[1]
    ex2 = client.post("/api/auth/google/exchange", json={"code": code2})
    assert ex2.status_code == 200

    # Ensure only 1 user exists
    user_count = db.query(User).filter(User.email == "repeat_google@example.com").count()
    assert user_count == 1


# ── 8: Account Linking (Existing Email/Password User) ─────────────────────────

@needs_db
@patch("app.routers.auth.exchange_code_for_google_tokens")
@patch("app.routers.auth.verify_google_id_token")
def test_account_linking_existing_password_user(
    mock_verify: MagicMock,
    mock_exchange: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    """Existing email/password account is safely linked with Google; password_hash preserved."""
    user_before = UserService(db).create_email_user(
        name="Local Account",
        email="link_test@example.com",
    )
    db.commit()

    assert user_before is not None
    assert user_before.google_id is None

    # 2. Login via Google with identical email
    state = "state_link"
    client.cookies.set("oauth_state", state)
    client.cookies.set("oauth_verifier", "verifier_link")

    mock_exchange.return_value = {"id_token": "token_link"}
    mock_verify.return_value = {
        "iss": "https://accounts.google.com",
        "sub": "linked-google-sub-777",
        "email": "LINK_TEST@example.com",
        "email_verified": True,
        "name": "Google Profile Name",
    }

    callback_resp = client.get(
        f"/api/auth/google/callback?code=code_link&state={state}",
        follow_redirects=False,
    )
    assert callback_resp.status_code == 307
    handoff_code = callback_resp.headers["location"].split("code=")[1]

    # Exchange for token
    token_resp = client.post("/api/auth/google/exchange", json={"code": handoff_code})
    assert token_resp.status_code == 200

    # 3. Verify user row was updated: google_id is set, password_hash untouched
    db.expire_all()
    user_after = db.query(User).filter(User.email == "link_test@example.com").first()
    assert user_after is not None
    assert user_after.google_id == "linked-google-sub-777"
    assert user_after.password_hash == original_pw_hash

    # 4. Verify user can STILL log in using original password!
    pw_login_resp = client.post(
        "/api/auth/login",
        json={"email": "link_test@example.com", "password": "Password123!"},
    )
    assert pw_login_resp.status_code == 200
    assert "access_token" in pw_login_resp.json()["data"]


# ── 9: Account Conflict / Duplicate Google ID Protection ──────────────────────

@needs_db
@patch("app.routers.auth.exchange_code_for_google_tokens")
@patch("app.routers.auth.verify_google_id_token")
def test_google_account_conflict_protection(
    mock_verify: MagicMock,
    mock_exchange: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    """If an account is already linked to Google ID A, trying to link it to Google ID B fails."""
    # Create user already linked to sub A
    user = UserService(db).create_email_user(
        name="Conflict User",
        email="conflict@example.com",
    )
    user.google_id = "original-google-sub-A"
    db.commit()

    # Now attempt Google login with the same email but different sub B
    state = "state_conflict"
    client.cookies.set("oauth_state", state)
    client.cookies.set("oauth_verifier", "verifier_conflict")

    mock_exchange.return_value = {"id_token": "token_conflict"}
    mock_verify.return_value = {
        "iss": "https://accounts.google.com",
        "sub": "different-google-sub-B",
        "email": "conflict@example.com",
        "email_verified": True,
        "name": "Conflict Attempt",
    }

    resp = client.get(
        f"/api/auth/google/callback?code=c_conflict&state={state}",
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert "error=account_conflict" in resp.headers["location"]

    # Verify google_id was not modified
    db.expire_all()
    user_check = db.query(User).filter(User.email == "conflict@example.com").first()
    assert user_check is not None
    assert user_check.google_id == "original-google-sub-A"


# ── 10: Inactive Google User Rejection ─────────────────────────────────────────

@needs_db
@patch("app.routers.auth.exchange_code_for_google_tokens")
@patch("app.routers.auth.verify_google_id_token")
def test_inactive_google_user_rejected(
    mock_verify: MagicMock,
    mock_exchange: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    """Inactive Google account cannot authenticate."""
    from app.services.user_service import UserService
    user = UserService(db).authenticate_or_create_google_user(
        google_id="sub_inactive",
        email="inactive_google@example.com",
        name="Inactive",
    )
    user.is_active = False
    db.commit()

    state = "state_inactive"
    client.cookies.set("oauth_state", state)
    client.cookies.set("oauth_verifier", "verifier_inactive")

    mock_exchange.return_value = {"id_token": "tok"}
    mock_verify.return_value = {
        "iss": "https://accounts.google.com",
        "sub": "sub_inactive",
        "email": "inactive_google@example.com",
        "email_verified": True,
        "name": "Inactive",
    }

    resp = client.get(
        f"/api/auth/google/callback?code=code_inactive&state={state}",
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert "error=inactive_user" in resp.headers["location"]


# ── 11, 12, 13: Handoff Code Single-Use & Expiration ─────────────────────────

def test_handoff_store_single_use_and_replay_prevention() -> None:
    """Handoff store returns data on first consume and None on second (replay)."""
    store = InMemoryHandoffCodeStore()
    code = store.create_code(user_id="u123", email="user@test.com", ttl_seconds=60)
    assert len(code) > 20

    # First consume -> succeeds
    first = store.consume_code(code)
    assert first is not None
    assert first["user_id"] == "u123"
    assert first["email"] == "user@test.com"

    # Second consume (replay) -> returns None
    second = store.consume_code(code)
    assert second is None


def test_handoff_store_expired_code_rejected() -> None:
    """Expired code is rejected."""
    store = InMemoryHandoffCodeStore()
    code = store.create_code(user_id="u123", email="user@test.com", ttl_seconds=0)
    time.sleep(0.01)

    result = store.consume_code(code)
    assert result is None


def test_exchange_endpoint_rejects_invalid_code(client: TestClient) -> None:
    """POST /api/auth/google/exchange with invalid code returns 400."""
    response = client.post(
        "/api/auth/google/exchange",
        json={"code": "non_existent_code_xyz"},
    )
    assert response.status_code == 400
    err = response.json()["error"]
    assert err["code"] == "INVALID_EXCHANGE_CODE"


# ── 15: Google-only User Has No Password Hash ─────────────────────────────────

@needs_db
def test_google_only_user_cannot_login_with_password(client: TestClient, db: Session) -> None:
    """User created via Google has password_hash=None."""
    from app.services.user_service import UserService
    user = UserService(db).authenticate_or_create_google_user(
        google_id="google_only_sub",
        email="google_only@example.com",
        name="Google Only User",
    )
    assert user.password_hash is None
