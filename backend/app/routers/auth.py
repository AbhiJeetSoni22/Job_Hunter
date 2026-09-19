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

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.core.oauth import (
    build_google_authorization_url,
    exchange_code_for_google_tokens,
    generate_oauth_state,
    generate_pkce_pair,
    get_handoff_store,
    verify_google_id_token,
)
from app.core.security import create_access_token
from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import (
    GoogleExchangeRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.job import ApiResponse
from app.services.user_service import (
    DuplicateEmailError,
    GoogleAccountConflictError,
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


# ── GET /api/auth/google ─────────────────────────────────────────────────────

@router.get(
    "/google",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Initiate Google OAuth 2.0 / OIDC login flow",
    description="Generates PKCE verifier and CSRF state cookies, then redirects to Google's OAuth consent screen.",
)
def google_auth() -> RedirectResponse:
    state = generate_oauth_state()
    verifier, challenge = generate_pkce_pair()
    auth_url = build_google_authorization_url(state=state, code_challenge=challenge)

    settings = get_settings()
    is_production = settings.APP_ENV == "production"

    response = RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        secure=is_production,
        max_age=300,
    )
    response.set_cookie(
        key="oauth_verifier",
        value=verifier,
        httponly=True,
        samesite="lax",
        secure=is_production,
        max_age=300,
    )
    return response


# ── GET /api/auth/google/callback ────────────────────────────────────────────

@router.get(
    "/google/callback",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Google OAuth 2.0 callback endpoint",
    description="Handles callback from Google, verifies state and ID token, provisions/links user, and redirects to frontend with single-use handoff code.",
)
def google_callback(
    request: Request,
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    settings = get_settings()

    def _error_redirect(error_code: str) -> RedirectResponse:
        err_response = RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error={error_code}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
        err_response.delete_cookie("oauth_state")
        err_response.delete_cookie("oauth_verifier")
        return err_response

    # Check for Google error response (e.g. user canceled)
    if error or not code:
        return _error_redirect(error or "google_auth_canceled")

    # Validate state for CSRF protection
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or not state or cookie_state != state:
        return _error_redirect("invalid_state")

    # Retrieve PKCE code verifier
    code_verifier = request.cookies.get("oauth_verifier")
    if not code_verifier:
        return _error_redirect("missing_verifier")

    # Exchange code for Google tokens
    try:
        token_data = exchange_code_for_google_tokens(code=code, code_verifier=code_verifier)
    except Exception:
        return _error_redirect("token_exchange_failed")

    # Verify ID token
    try:
        claims = verify_google_id_token(token_data["id_token"])
    except Exception:
        return _error_redirect("invalid_identity")

    google_sub = claims["sub"]
    google_email = claims["email"]
    google_name = claims.get("name") or claims.get("given_name") or "Google User"

    # Authenticate, link, or provision user
    try:
        user = UserService(db).authenticate_or_create_google_user(
            google_id=google_sub,
            email=google_email,
            name=google_name,
        )
    except InactiveUserError:
        return _error_redirect("inactive_user")
    except GoogleAccountConflictError:
        return _error_redirect("account_conflict")
    except Exception:
        return _error_redirect("auth_failed")

    # Create temporary, single-use, short-lived handoff code (60s TTL)
    handoff_code = get_handoff_store().create_code(
        user_id=str(user.id),
        email=user.email,
        ttl_seconds=60,
    )

    success_response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?code={handoff_code}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    success_response.delete_cookie("oauth_state")
    success_response.delete_cookie("oauth_verifier")
    return success_response


# ── POST /api/auth/google/exchange ───────────────────────────────────────────

@router.post(
    "/google/exchange",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Exchange single-use handoff code for application JWT access token",
    description="Validates and immediately consumes the temporary authorization code, issuing the final application JWT.",
)
def google_exchange(
    body: GoogleExchangeRequest,
    db: DbSession,
) -> ApiResponse[TokenResponse]:
    data = get_handoff_store().consume_code(body.code)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_EXCHANGE_CODE", "message": "The authorization code is invalid or has expired."},
        )

    user = UserService(db).get_by_id(data["user_id"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User account not found."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INACTIVE_USER", "message": "User account is inactive."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_str = create_access_token(data={"sub": str(user.id), "email": user.email})
    return ApiResponse(data=TokenResponse(access_token=token_str, token_type="bearer"))
