"""
Application configuration.

All settings are read from environment variables (or a .env file).
Accessing settings.GEMINI_API_KEY anywhere in the codebase will raise
a clear error at startup if the variable is missing — not at call time.
"""

from functools import lru_cache
from typing import Any

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: PostgresDsn

    # ── Gemini AI ──────────────────────────────────────────────────────────
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── JWT Authentication ──────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "dev-insecure-jwt-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days (10080 minutes)

    # ── Resend Email Service ───────────────────────────────────────────────
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "Job Hunter <onboarding@resend.dev>"

    # ── Google OAuth 2.0 / OpenID Connect ───────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Application ────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── CORS ───────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins.
    # Example: "http://localhost:3000,https://myapp.com"
    CORS_ORIGINS: str = "http://localhost:3000"

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed = {"development", "production", "test"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("JWT_SECRET_KEY must not be empty")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate production security configuration after model initialization."""
        insecure_defaults = {
            "dev-insecure-jwt-secret-key-change-this-in-production",
            "dev-insecure-jwt-secret-key-change-in-production",
            "secret",
            "changeme",
        }
        if (
            self.APP_ENV in {"production", "prod"}
            and (not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY.lower().strip() in insecure_defaults)
        ):
            raise ValueError(
                "JWT_SECRET_KEY is insecure or unset for production environment! "
                "Set a strong secret in environment variables."
            )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def database_url_str(self) -> str:
        """Return DATABASE_URL as a plain string for SQLAlchemy."""
        return str(self.DATABASE_URL)


@lru_cache
def get_settings() -> Settings:
    """
    Return cached Settings instance.

    lru_cache ensures the .env file is read exactly once per process.
    Use get_settings() everywhere — never instantiate Settings() directly.
    """
    return Settings()  # type: ignore[call-arg]