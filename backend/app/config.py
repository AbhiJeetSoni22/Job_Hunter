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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours (1440 minutes)

    # ── Limits & Abuse Protection ──────────────────────────────────────────
    MAX_BULK_SCORE_LIMIT: int = 100
    SCRAPER_COOLDOWN_SECONDS: int = 60
    AI_RATE_LIMIT_PER_MINUTE: int = 30

    # ── Brevo HTTP API Email Service ───────────────────────────────────────
    BREVO_API_KEY: str = ""
    EMAIL_FROM_ADDRESS: str = "your-sender@example.com"
    EMAIL_FROM_NAME: str = "Job Hunter"

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

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        allowed_algorithms = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
        if not v or v.strip().upper() not in allowed_algorithms:
            raise ValueError(f"JWT_ALGORITHM '{v}' is unsupported or insecure. Allowed: {sorted(allowed_algorithms)}")
        return v.strip().upper()

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_access_token_expire_minutes(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")
        return v

    @field_validator("MAX_BULK_SCORE_LIMIT")
    @classmethod
    def validate_max_bulk_score_limit(cls, v: int) -> int:
        if v <= 0 or v > 500:
            raise ValueError("MAX_BULK_SCORE_LIMIT must be between 1 and 500")
        return v

    @field_validator("SCRAPER_COOLDOWN_SECONDS")
    @classmethod
    def validate_scraper_cooldown_seconds(cls, v: int) -> int:
        if v < 0:
            raise ValueError("SCRAPER_COOLDOWN_SECONDS cannot be negative")
        return v

    @field_validator("AI_RATE_LIMIT_PER_MINUTE")
    @classmethod
    def validate_ai_rate_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("AI_RATE_LIMIT_PER_MINUTE must be greater than 0")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate production security configuration after model initialization."""
        insecure_defaults = {
            "dev-insecure-jwt-secret-key-change-this-in-production",
            "dev-insecure-jwt-secret-key-change-in-production",
            "change-this-to-a-secure-secret-key-in-production",
            "secret",
            "changeme",
            "password",
            "12345678",
            "admin",
            "jwtsecret",
            "supersecret",
        }
        if self.APP_ENV in {"production", "prod"}:
            secret = (self.JWT_SECRET_KEY or "").strip()
            if not secret or secret.lower() in insecure_defaults:
                raise ValueError(
                    "JWT_SECRET_KEY is insecure or unset for production environment! "
                    "Set a strong secret in environment variables."
                )
            if len(secret) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY is too short for production environment! "
                    "Set a strong secret of at least 32 characters in environment variables."
                )

            # CORS validation for production
            cors_raw = (self.CORS_ORIGINS or "").strip()
            if not cors_raw:
                raise ValueError("CORS_ORIGINS must be explicitly configured in production environment.")
            
            origins = self.cors_origins_list
            if "*" in origins or cors_raw == "*":
                raise ValueError(
                    "CORS_ORIGINS cannot contain wildcard '*' in production when credentials/authentication are enabled."
                )
            for origin in origins:
                if not (origin.startswith("http://") or origin.startswith("https://")):
                    raise ValueError(
                        f"CORS origin '{origin}' is invalid. Must include http:// or https:// protocol scheme."
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