"""
Email service.

Handles sending transactional emails via Resend HTTP API.
Uses the official Resend Python SDK.
"""

import logging
import os
from typing import Any

import resend
from resend.exceptions import ResendError

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when an email fails to deliver via Resend."""
    pass


def _mask_email(email: str) -> str:
    """Mask email address for privacy in logs (e.g. u***r@example.com)."""
    if not email or "@" not in email:
        return "***"
    local_part, domain = email.strip().split("@", 1)
    if len(local_part) <= 1:
        masked_local = f"{local_part}***"
    else:
        masked_local = f"{local_part[0]}***{local_part[-1]}"
    return f"{masked_local}@{domain}"


class EmailService:
    """Service for dispatching transactional emails via Resend HTTP API."""

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.RESEND_API_KEY
        self._from_email = from_email if from_email is not None else settings.RESEND_FROM_EMAIL

    def send_otp_email(self, to_email: str, otp_code: str) -> bool:
        """
        Send a 6-digit verification code to the recipient's email address via Resend HTTP API.

        In production, requires a valid RESEND_API_KEY.
        In development/test environments without an API key, logs the code safely
        so developers and local users can still complete the authentication flow.

        Raises:
            EmailDeliveryError: if API key is missing in production or Resend API dispatch fails.
        """
        settings = get_settings()
        app_env = os.environ.get("APP_ENV") or settings.APP_ENV

        is_configured = bool(self._api_key and self._api_key.strip())

        if not is_configured:
            if app_env in {"production", "prod"}:
                logger.error("Resend API key is not configured in production!")
                raise EmailDeliveryError("Email service is not configured. Please contact support.")
            logger.info(
                "[DEV/TEST] Resend API key not set. Verification OTP for %s: %s",
                to_email,
                otp_code,
            )
            return True

        masked_to = _mask_email(to_email)
        subject = f"{otp_code} is your Job Hunter verification code"
        from_header = (
            self._from_email.strip()
            if self._from_email and self._from_email.strip()
            else "Job Hunter <onboarding@resend.dev>"
        )

        plain_text = (
            f"Your Job Hunter verification code is: {otp_code}\n\n"
            "This code expires in 10 minutes and can only be used once.\n\n"
            "If you did not request this verification code, you can safely ignore this email."
        )

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

        params: resend.Emails.SendParams = {
            "from": from_header,
            "to": [to_email.strip()],
            "subject": subject,
            "text": plain_text,
            "html": html_content,
        }

        try:
            logger.info("Dispatching OTP email to recipient=%s via Resend API", masked_to)
            resend.api_key = self._api_key.strip()
            response: Any = resend.Emails.send(params)
            email_id = getattr(response, "id", None) or (response.get("id") if isinstance(response, dict) else None)
            logger.info("Successfully dispatched OTP email to recipient=%s via Resend API (id=%s)", masked_to, email_id)
            return True
        except ResendError as exc:
            error_code = getattr(exc, "code", None)
            error_msg = getattr(exc, "message", str(exc))
            logger.error(
                "Resend email delivery failed recipient=%s status=%s: %s",
                masked_to,
                error_code,
                error_msg,
            )
            raise EmailDeliveryError("Failed to deliver verification email. Please try again.") from exc
        except Exception as exc:
            logger.error(
                "Unexpected error during Resend email delivery recipient=%s: %s",
                masked_to,
                exc.__class__.__name__,
            )
            raise EmailDeliveryError("An unexpected error occurred while sending verification email.") from exc
