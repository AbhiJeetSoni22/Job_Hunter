"""
Email service.

Handles sending transactional emails via Resend API (https://resend.com).
Uses httpx client for HTTP communication.
"""

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailDeliveryError(Exception):
    """Raised when an email fails to deliver via Resend."""
    pass


class EmailService:
    """Service for dispatching transactional emails."""

    def __init__(self, api_key: str | None = None, from_email: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.RESEND_API_KEY
        self._from_email = from_email if from_email is not None else settings.RESEND_FROM_EMAIL

    def send_otp_email(self, to_email: str, otp_code: str) -> bool:
        """
        Send a 6-digit verification code to the recipient's email address.

        In production, requires a valid RESEND_API_KEY.
        In development/test environments without an API key, logs the code safely
        so developers and local users can still complete the authentication flow.

        Raises:
            EmailDeliveryError: if Resend returns a non-2xx error or network failure.
        """
        settings = get_settings()
        import os
        app_env = os.environ.get("APP_ENV") or settings.APP_ENV

        if not self._api_key or self._api_key.strip() == "":
            if app_env in {"production", "prod"}:
                logger.error("RESEND_API_KEY is not configured in production!")
                raise EmailDeliveryError("Email service is not configured. Please contact support.")
            logger.info(
                "[DEV/TEST] RESEND_API_KEY not set. Verification OTP for %s: %s",
                to_email,
                otp_code,
            )
            return True

        subject = f"{otp_code} is your Job Hunter verification code"
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verification Code</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0f172a; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" max-width="500" border="0" cellspacing="0" cellpadding="0" style="max-width: 500px; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; padding: 36px; text-align: center;">
          <tr>
            <td align="center">
              <h2 style="margin: 0 0 8px 0; font-size: 22px; font-weight: 700; color: #38bdf8; letter-spacing: -0.5px;">Job Hunter</h2>
              <p style="margin: 0 0 24px 0; font-size: 14px; color: #94a3b8;">AI Internship Acquisition System</p>
              
              <div style="background-color: #0f172a; border-radius: 8px; border: 1px solid #334155; padding: 24px; margin: 24px 0;">
                <p style="margin: 0 0 12px 0; font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">Your verification code</p>
                <div style="font-size: 36px; font-weight: 800; letter-spacing: 6px; color: #ffffff; font-family: monospace;">{otp_code}</div>
              </div>

              <p style="margin: 0 0 12px 0; font-size: 13px; color: #cbd5e1;">
                This code expires in <strong>10 minutes</strong> and can only be used once.
              </p>
              <p style="margin: 0; font-size: 12px; color: #64748b;">
                If you did not request this verification code, you can safely ignore this email.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

        payload: dict[str, Any] = {
            "from": self._from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key.strip()}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except Exception as exc:
            logger.error("Failed to connect to Resend API: %s", exc)
            raise EmailDeliveryError("Failed to dispatch verification email. Please try again.") from exc

        if response.status_code not in {200, 201}:
            logger.error("Resend API error %s: %s", response.status_code, response.text)
            raise EmailDeliveryError(f"Email delivery service returned an error ({response.status_code}).")

        logger.info("Successfully dispatched OTP email to %s via Resend", to_email)
        return True
