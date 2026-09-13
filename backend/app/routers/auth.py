"""
Auth router — Authentication and user identity endpoints.

Handles HTTP concerns for:
    POST /api/auth/register — register new user account
    POST /api/auth/login    — authenticate user and issue JWT token
    GET  /api/auth/me       — return profile of currently authenticated user

Rules (ARCHITECTURE.md):
    - Thin router: no business logic or direct DB calls.
    - Delegate everything to UserService and security utilities.
    - Standard ApiResponse[T] envelope used for all responses.
"""

from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token
from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.schemas.job import ApiResponse
from app.services.user_service import (
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    UserService,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── POST /api/auth/register ──────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Registers a new user account with name, email, and password. Returns user profile (excluding password_hash).",
)
def register(
    body: UserRegisterRequest,
    db: DbSession,
) -> ApiResponse[UserResponse]:
    try:
        user = UserService(db).register_user(body)
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_ALREADY_EXISTS", "message": str(exc)},
        ) from exc

    return ApiResponse(data=UserResponse.model_validate(user))


# ── POST /api/auth/login ─────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain access token",
    description="Authenticates email and password, returning an OAuth2-compatible Bearer JWT token.",
)
def login(
    body: UserLoginRequest,
    db: DbSession,
) -> ApiResponse[TokenResponse]:
    try:
        user = UserService(db).authenticate_user(body)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INACTIVE_USER", "message": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    token_str = create_access_token(data={"sub": str(user.id), "email": user.email})
    return ApiResponse(data=TokenResponse(access_token=token_str, token_type="bearer"))


# ── GET /api/auth/me ─────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user identified by the Bearer token.",
)
def get_me(current_user: CurrentUser) -> ApiResponse[UserResponse]:
    return ApiResponse(data=UserResponse.model_validate(current_user))
