"""
Shared FastAPI dependencies.

Import these in routers:

from app.dependencies import DbSession, CurrentUser, get_active_resume, get_current_user

This module provides reusable dependency aliases and higher-level
dependencies built on top of app.database.get_db().
"""

from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.resume import Resume
from app.models.user import User
from app.services.user_service import UserService

# ── Security Scheme ─────────────────────────────────────────────────────────
# HTTPBearer auto_error=False allows us to return custom envelope errors (ApiResponse)
security_scheme = HTTPBearer(auto_error=False)


# ── Type Aliases ─────────────────────────────────────────────────────────────
DbSession = Annotated[Session, Depends(get_db)]


# ── Auth Dependency ──────────────────────────────────────────────────────────

def get_current_user(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> User:
    """
    FastAPI dependency — validates Authorization Bearer JWT token and resolves to User.

    Raises:
      - 401 INVALID_TOKEN: if Authorization header is missing, malformed, or signature invalid.
      - 401 TOKEN_EXPIRED: if JWT expiration timestamp has passed.
      - 401 USER_NOT_FOUND: if subject user ID does not exist in DB.
      - 401 INACTIVE_USER: if target user account is deactivated.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Missing authentication token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Authentication token has expired"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid authentication token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token missing subject claim"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = UserService(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User account not found"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INACTIVE_USER", "message": "User account is inactive"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Active Resume Dependency ─────────────────────────────────────────────────

def get_active_resume(
    user: CurrentUser,
    db: DbSession,
) -> Resume:
    """
    FastAPI dependency — resolves to the most recently uploaded resume for the authenticated user.

    Raises HTTP 422 NO_RESUME when no resume exists for the user.
    Declared as Depends in any endpoint that requires a resume.
    """
    resume = (
        db.query(Resume)
        .filter(Resume.user_id == user.id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "NO_RESUME",
                "message": "Upload a resume before scoring jobs",
            },
        )
    return resume