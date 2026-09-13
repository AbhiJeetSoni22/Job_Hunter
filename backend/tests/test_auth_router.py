"""
tests/test_auth_router.py — HTTP-level integration tests for auth router (/api/auth).

Uses FastAPI TestClient to test real HTTP request/response envelope behavior:
  - POST /api/auth/register → 201 Created
  - Duplicate registration → 409 EMAIL_ALREADY_EXISTS
  - POST /api/auth/login → 200 OK
  - Invalid credentials → 401 INVALID_CREDENTIALS
  - GET /api/auth/me with valid token → 200 OK
  - GET /api/auth/me without token → 401 INVALID_TOKEN
  - GET /api/auth/me with invalid/expired token → 401 INVALID_TOKEN / TOKEN_EXPIRED
"""

from datetime import timedelta

import pytest

from app.core.security import create_access_token
from app.schemas.auth import UserRegisterRequest
from app.services.user_service import UserService
from tests.conftest import needs_db


def test_http_register_success(client):
    """POST /api/auth/register returns 201 and ApiResponse[UserResponse]."""
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Integration User",
            "email": "http_user@example.com",
            "password": "Password123!",
        },
    )
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["error"] is None
    data = json_data["data"]
    assert data["email"] == "http_user@example.com"
    assert data["name"] == "Integration User"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_http_register_duplicate_email(client):
    """Duplicate registration returns 409 Conflict with EMAIL_ALREADY_EXISTS error code."""
    client.post(
        "/api/auth/register",
        json={
            "name": "Original User",
            "email": "dup_http@example.com",
            "password": "Password123!",
        },
    )

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Duplicate User",
            "email": "DUP_HTTP@example.com",
            "password": "Password456!",
        },
    )
    assert response.status_code == 409
    json_data = response.json()
    assert json_data["data"] is None
    error = json_data["error"]
    assert error["code"] == "EMAIL_ALREADY_EXISTS"
    assert "already exists" in error["message"]


def test_http_login_success(client):
    """POST /api/auth/login returns 200 OK and TokenResponse envelope."""
    client.post(
        "/api/auth/register",
        json={
            "name": "Login HTTP User",
            "email": "login_http@example.com",
            "password": "Password123!",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "LOGIN_HTTP@example.com",
            "password": "Password123!",
        },
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["error"] is None
    data = json_data["data"]
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20


def test_http_login_invalid_credentials(client):
    """POST /api/auth/login with wrong password returns 401 INVALID_CREDENTIALS."""
    client.post(
        "/api/auth/register",
        json={
            "name": "Wrong Pass User",
            "email": "wrong_pass@example.com",
            "password": "RightPassword123!",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "wrong_pass@example.com",
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401
    json_data = response.json()
    assert json_data["data"] is None
    error = json_data["error"]
    assert error["code"] == "INVALID_CREDENTIALS"


def test_http_get_me_valid_token(client):
    """GET /api/auth/me with valid Bearer token returns 200 OK and UserResponse envelope."""
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "name": "Me Endpoint User",
            "email": "me_user@example.com",
            "password": "Password123!",
        },
    )
    user_id = reg_resp.json()["data"]["id"]

    login_resp = client.post(
        "/api/auth/login",
        json={
            "email": "me_user@example.com",
            "password": "Password123!",
        },
    )
    token = login_resp.json()["data"]["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["error"] is None
    data = json_data["data"]
    assert data["id"] == user_id
    assert data["email"] == "me_user@example.com"
    assert data["name"] == "Me Endpoint User"


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
    user = UserService(db).register_user(UserRegisterRequest(
        name="Expired User",
        email="expired_http@example.com",
        password="Password123!",
    ))

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
