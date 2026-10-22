"""
GitHub Actions repository_dispatch service.

Triggers background worker workflows on GitHub Actions via the repository_dispatch API:
    POST https://api.github.com/repos/{owner}/{repo}/dispatches

Requirements:
- Narrowly scoped fine-grained GitHub token (Contents: Read and write).
- Zero token leakage in exceptions, logs, or API responses.
- Bounded connection and read timeouts.
- Safe failure handling: failure never fails or rolls back database tasks.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10.0
GITHUB_API_VERSION = "2022-11-28"


class GitHubDispatchError(Exception):
    """Raised when GitHub dispatch fails and raise_on_error is True."""


def mask_token(token: str) -> str:
    """Mask token showing only a suffix or '***'."""
    if not token:
        return ""
    if len(token) <= 8:
        return "***"
    return f"***{token[-4:]}"


def sanitize_error_message(message: str, token: str | None = None) -> str:
    """
    Remove sensitive credentials such as database passwords, API keys, or GitHub tokens from error messages.
    """
    if not message:
        return ""

    sanitized = message

    # Redact explicit token value if passed
    if token and token in sanitized:
        sanitized = sanitized.replace(token, "***REDACTED_TOKEN***")

    # Redact Bearer tokens in headers or strings
    sanitized = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer ***", sanitized, flags=re.IGNORECASE)

    # Redact GitHub token patterns (ghp_..., github_pat_...)
    sanitized = re.sub(r"gh[pousr]_[A-Za-z0-9_]{30,}", "ghp_***", sanitized)
    sanitized = re.sub(r"github_pat_[A-Za-z0-9_]{30,}", "github_pat_***", sanitized)

    # Redact database passwords in connection URLs: postgresql://user:password@host:port/db
    sanitized = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", sanitized)

    # Redact common key=value secret patterns
    sanitized = re.sub(
        r"(password|secret|key|token|authorization)=([^\s,;]+)",
        r"\1=***",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


class GitHubDispatchService:
    """
    Service for triggering GitHub Actions workflows via repository_dispatch API.
    """

    def __init__(
        self,
        token: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        httpx_client: httpx.Client | None = None,
    ) -> None:
        settings = get_settings()
        self._token = (
            token.strip()
            if token is not None
            else getattr(settings, "GITHUB_DISPATCH_TOKEN", "").strip()
        )
        self._owner = (
            owner.strip()
            if owner is not None
            else getattr(settings, "GITHUB_REPO_OWNER", "").strip()
        )
        self._repo = (
            repo.strip()
            if repo is not None
            else getattr(settings, "GITHUB_REPO_NAME", "").strip()
        )
        self._timeout = httpx.Timeout(timeout_seconds, connect=min(5.0, timeout_seconds))
        self._custom_client = httpx_client

    @property
    def is_configured(self) -> bool:
        """Return True if token, owner, and repository name are all populated."""
        return bool(self._token and self._owner and self._repo)

    @property
    def dispatch_url(self) -> str:
        """Return the target GitHub repository_dispatch endpoint URL."""
        return f"https://api.github.com/repos/{self._owner}/{self._repo}/dispatches"

    def sanitize_error(self, message: str) -> str:
        """Sanitize message using instance token."""
        return sanitize_error_message(message, token=self._token)

    def dispatch_task_queue(
        self,
        event_type: str = "process_task_queue",
        client_payload: dict[str, Any] | None = None,
        raise_on_error: bool = False,
    ) -> bool:
        """
        Trigger GitHub Actions workflow by dispatching repository_dispatch event.

        Args:
            event_type: The dispatch event type matching the workflow trigger (default: 'process_task_queue').
            client_payload: Optional JSON metadata passed to the workflow run.
            raise_on_error: If True, raises GitHubDispatchError on failure; if False, logs safe warning and returns False.

        Returns:
            True if GitHub returned HTTP 204 No Content, False otherwise.
        """
        if not self.is_configured:
            logger.warning(
                "GitHub Actions dispatch skipped: GITHUB_DISPATCH_TOKEN, GITHUB_REPO_OWNER, "
                "or GITHUB_REPO_NAME is unset."
            )
            if raise_on_error:
                raise GitHubDispatchError(
                    "GitHub dispatch is not configured (missing token, owner, or repo)"
                )
            return False

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        payload: dict[str, Any] = {"event_type": event_type}
        if client_payload:
            payload["client_payload"] = client_payload

        try:
            if self._custom_client is not None:
                response = self._custom_client.post(self.dispatch_url, headers=headers, json=payload)
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(self.dispatch_url, headers=headers, json=payload)

            if response.status_code == 204:
                logger.info(
                    "GitHub Actions dispatch successful for repo %s/%s (event: %s)",
                    self._owner,
                    self._repo,
                    event_type,
                )
                return True

            safe_body = self.sanitize_error(response.text[:500])
            logger.warning(
                "GitHub Actions dispatch rejected for repo %s/%s with HTTP %d: %s",
                self._owner,
                self._repo,
                response.status_code,
                safe_body,
            )
            if raise_on_error:
                raise GitHubDispatchError(
                    f"GitHub dispatch failed with HTTP {response.status_code}: {safe_body}"
                )
            return False

        except httpx.TimeoutException as exc:
            safe_err = self.sanitize_error(str(exc))
            logger.warning(
                "GitHub Actions dispatch timed out for repo %s/%s: %s",
                self._owner,
                self._repo,
                safe_err,
            )
            if raise_on_error:
                raise GitHubDispatchError(f"GitHub dispatch timed out: {safe_err}") from exc
            return False

        except httpx.RequestError as exc:
            safe_err = self.sanitize_error(str(exc))
            logger.warning(
                "GitHub Actions dispatch network error for repo %s/%s: %s",
                self._owner,
                self._repo,
                safe_err,
            )
            if raise_on_error:
                raise GitHubDispatchError(f"GitHub dispatch network error: {safe_err}") from exc
            return False

        except Exception as exc:
            safe_err = self.sanitize_error(str(exc))
            logger.warning(
                "Unexpected error during GitHub Actions dispatch for repo %s/%s: %s",
                self._owner,
                self._repo,
                safe_err,
            )
            if raise_on_error:
                raise GitHubDispatchError(f"Unexpected dispatch error: {safe_err}") from exc
            return False
