"""
Pydantic schemas for authentication and user endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ── Inbound Requests ─────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    """Payload for POST /api/auth/register."""

    name: str = Field(..., min_length=1, max_length=255, description="Full display name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password (min 8 chars)")

    @field_validator("name", "email")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class UserLoginRequest(BaseModel):
    """Payload for POST /api/auth/login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="Account password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class GoogleExchangeRequest(BaseModel):
    """Payload for POST /api/auth/google/exchange."""

    code: str = Field(..., min_length=1, description="Temporary single-use handoff authorization code")


# ── Outbound Responses ────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Public user profile response payload. Excludes password_hash completely."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """OAuth2-compatible Bearer access token response."""

    access_token: str
    token_type: str = "bearer"
