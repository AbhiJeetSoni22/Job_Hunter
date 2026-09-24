"""
Auth router — Authentication and user identity endpoints.

Handles HTTP concerns for:
    POST /api/auth/otp/request       — request 6-digit email OTP
    POST /api/auth/otp/verify        — verify email OTP and issue JWT token
    GET  /api/auth/me                — return profile of currently authenticated user
    GET  /api/auth/google            — initiate Google OAuth 2.0 / OIDC flow
    GET  /api/auth/google/callback   — Google OAuth callback endpoint
    POST /api/auth/google/exchange   — exchange single-use handoff code for JWT token

Rules (ARCHITECTURE.md):
    - Thin router: no business logic or direct DB calls.
    - Delegate to OtpService, UserService, and security utilities.
    - Standard ApiResponse[T] envelope used for all responses.
    - OTP-only email authentication + Google OAuth. No passwords.
"""

import logging
from typing import Literal

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
    OtpRequest,
    OtpResponse,
    OtpVerifyRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.job import ApiResponse
from app.services.email_service import EmailDeliveryError
from app.services.otp_service import (
    InvalidOtpError,
    OtpRateLimitError,
    OtpService,
    OtpTooManyAttemptsError,
)
from app.services.user_service import (
    GoogleAccountConflictError,
    InactiveUserError,
    UserService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Cookie Configuration Helpers ─────────────────────────────────────────────

def _is_secure_request(request: Request) -> bool:
    """
    Determine if the request is running in a secure (HTTPS) environment.

    Checks:
      1. APP_ENV is explicitly 'production' or 'prod'
      2. X-Forwarded-Proto header is 'https' (behind Render / Cloudflare / reverse proxy)
      3. Direct request URL scheme is 'https'
      4. Configured GOOGLE_REDIRECT_URI starts with 'https://'
    """
    settings = get_settings()
    if settings.APP_ENV in {"production", "prod"}:
        return True
    if request.headers.get("x-forwarded-proto", "").lower() == "https":
        return True
    if request.url.scheme == "https":
        return True
    return settings.GOOGLE_REDIRECT_URI.lower().startswith("https://")


def _get_oauth_cookie_options(request: Request) -> tuple[bool, Literal["none", "lax"]]:
    """
    Return (secure, samesite) settings for OAuth state & verifier cookies.

    - In HTTPS production: secure=True and samesite="none" are required so the
      browser includes the cookies when Google redirects back cross-site to the callback.
    - In local HTTP development: secure=False and samesite="lax" are required because
      browsers reject SameSite=None when Secure is false.
    """
    is_secure = _is_secure_request(request)
    samesite_policy: Literal["none", "lax"] = "none" if is_secure else "lax"
    return is_secure, samesite_policy


# ── POST /api/auth/otp/request ───────────────────────────────────────────────

@router.post(
    "/otp/request",
    response_model=ApiResponse[OtpResponse],
    status_code=status.HTTP_200_OK,
    summary="Request a 6-digit email verification code",
    description="Generates a 6-digit OTP, stores its secure salted hash, and dispatches it via Resend.",
)
def request_otp(
    body: OtpRequest,
    db: DbSession,
) -> ApiResponse[OtpResponse]:
    try:
        OtpService(db).request_otp(body.email)
    except OtpRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": str(exc)},
        ) from exc
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EMAIL_DELIVERY_FAILED", "message": str(exc)},
        ) from exc

    return ApiResponse(
        data=OtpResponse(
            message="Verification code sent to your email.",
            email=body.email,
        )
    )


# ── POST /api/auth/otp/verify ────────────────────────────────────────────────

@router.post(
    "/otp/verify",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Verify email OTP and obtain access token",
    description="Verifies the 6-digit OTP code, provisions or authenticates the user, and returns an access token.",
)
def verify_otp(
    body: OtpVerifyRequest,
    db: DbSession,
) -> ApiResponse[TokenResponse]:
    try:
        user = OtpService(db).verify_otp(email=body.email, plain_otp=body.otp)
    except InvalidOtpError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_OTP", "message": str(exc)},
        ) from exc
    except OtpTooManyAttemptsError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "TOO_MANY_ATTEMPTS", "message": str(exc)},
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
def google_auth(request: Request) -> RedirectResponse:
    state = generate_oauth_state()
    verifier, challenge = generate_pkce_pair()
    auth_url = build_google_authorization_url(state=state, code_challenge=challenge)

    is_secure, samesite_policy = _get_oauth_cookie_options(request)

    response = RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite=samesite_policy,
        secure=is_secure,
        path="/",
        max_age=300,
    )
    response.set_cookie(
        key="oauth_verifier",
        value=verifier,
        httponly=True,
        samesite=samesite_policy,
        secure=is_secure,
        path="/",
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
    is_secure, samesite_policy = _get_oauth_cookie_options(request)
    frontend_base = settings.FRONTEND_URL.rstrip("/")

    def _error_redirect(error_code: str) -> RedirectResponse:
        err_response = RedirectResponse(
            url=f"{frontend_base}/login?error={error_code}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
        err_response.delete_cookie(
            "oauth_state",
            path="/",
            httponly=True,
            samesite=samesite_policy,
            secure=is_secure,
        )
        err_response.delete_cookie(
            "oauth_verifier",
            path="/",
            httponly=True,
            samesite=samesite_policy,
            secure=is_secure,
        )
        return err_response

    # Check for Google error response (e.g. user canceled)
    if error or not code:
        return _error_redirect(error or "google_auth_canceled")

    # Validate state for CSRF protection
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or not state or cookie_state != state:
        logger.warning(
            "OAuth state validation failed: cookie_present=%s, state_param_present=%s, match=%s",
            cookie_state is not None,
            state is not None,
            cookie_state == state if (cookie_state and state) else False,
        )
        return _error_redirect("invalid_state")

    # Retrieve PKCE code verifier
    code_verifier = request.cookies.get("oauth_verifier")
    if not code_verifier:
        logger.warning("OAuth PKCE verifier cookie missing in callback request")
        return _error_redirect("missing_verifier")

    # Exchange code for Google tokens
    try:
        token_data = exchange_code_for_google_tokens(code=code, code_verifier=code_verifier)
    except Exception:
        return _error_redirect("token_exchange_failed")

    # Verify ID token
    try:
        claims = verify_google_id_token(token_data["id_token"])
    except Exception as exc:
        logger.error("Google ID token verification failed: %s", exc)
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
        url=f"{frontend_base}/auth/callback?code={handoff_code}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    success_response.delete_cookie(
        "oauth_state",
        path="/",
        httponly=True,
        samesite=samesite_policy,
        secure=is_secure,
    )
    success_response.delete_cookie(
        "oauth_verifier",
        path="/",
        httponly=True,
        samesite=samesite_policy,
        secure=is_secure,
    )
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
