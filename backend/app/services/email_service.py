"""
Email service.

Handles sending transactional emails via Brevo HTTP API.
Provides detailed diagnostic logging for cloud hosting environments.
"""

import logging
import os
import httpx
from contextlib import suppress

from app.config import get_settings

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 10.0


class EmailDeliveryError(Exception):
    """Raised when an email fails to deliver via email provider."""
    pass


def mask_email(email: str) -> str:
    """Mask email address for privacy in logs (e.g. u***r@example.com)."""
    if not email or "@" not in email:
        return "***"
    local_part, domain = email.strip().split("@", 1)
    if len(local_part) <= 1:
        masked_local = f"{local_part}***"
    else:
        masked_local = f"{local_part[0]}***{local_part[-1]}"
    return f"{masked_local}@{domain}"


_mask_email = mask_email


class EmailService:
    """Service for dispatching transactional emails via Brevo HTTP API."""

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> None:
        settings = get_settings()
        raw_api_key = api_key if api_key is not None else getattr(settings, "BREVO_API_KEY", "")
        raw_from_email = from_email if from_email is not None else getattr(settings, "EMAIL_FROM_ADDRESS", "")
        raw_from_name = from_name if from_name is not None else getattr(settings, "EMAIL_FROM_NAME", "")

        self._api_key = raw_api_key.strip() if raw_api_key else ""
        self._from_email = raw_from_email.strip() if raw_from_email else ""
        self._from_name = raw_from_name.strip() if raw_from_name else "Job Hunter"

    def send_otp_email(self, to_email: str, otp_code: str) -> bool:
        """
        Send a 6-digit verification code to the recipient's email address via Brevo API.

        In production, requires valid credentials (BREVO_API_KEY).
        In development/test environments without credentials, logs the code safely
        so developers and local users can still complete the authentication flow.

        Raises:
            EmailDeliveryError: if connection, authentication, or dispatch fails.
        """
        settings = get_settings()
        app_env = os.environ.get("APP_ENV") or settings.APP_ENV

        is_configured = bool(self._api_key)

        logger.info(
            "BREVO DEBUG: api_key_configured=%s",
            is_configured,
        )

        if not is_configured:
            if app_env in {"production", "prod"}:
                logger.error("Email credentials (BREVO_API_KEY) are not configured in production!")
                raise EmailDeliveryError("Email service is not configured. Please contact support.")
            logger.info(
                "[DEV/TEST] Email credentials not set. Verification OTP for %s: %s",
                to_email,
                otp_code,
            )
            return True

        masked_to = _mask_email(to_email)
        subject = f"{otp_code} is your Job Hunter verification code"
        
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
        
        payload = {
            "sender": {
                "name": self._from_name,
                "email": self._from_email
            },
            "to": [
                {
                    "email": to_email.strip()
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": plain_text
        }

        headers = {
            "api-key": self._api_key,
            "accept": "application/json"
        }

        logger.info("BREVO DEBUG: Sending HTTP POST to api.brevo.com for %s...", masked_to)
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
                response = client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                logger.info("BREVO DEBUG: Message successfully accepted by Brevo for %s (status=%s)", masked_to, response.status_code)

        except httpx.ConnectError as exc:
            logger.error("BREVO connection failure: %s", exc)
            raise EmailDeliveryError("Failed to connect to email delivery server. Please try again.") from exc
        except httpx.TimeoutException as exc:
            logger.error("BREVO connection timed out after %.1fs: %s", HTTP_TIMEOUT_SECONDS, exc)
            raise EmailDeliveryError("Failed to connect to email delivery server. Please try again.") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "BREVO HTTP error: status_code=%s response=%s",
                exc.response.status_code,
                exc.response.text
            )
            if exc.response.status_code in {401, 403}:
                raise EmailDeliveryError("Failed to authenticate with email delivery server.") from exc
            
            raise EmailDeliveryError("Failed to dispatch verification email. Please try again.") from exc
        except httpx.RequestError as exc:
            logger.error("BREVO request error: %s", exc)
            raise EmailDeliveryError("Failed to connect to email delivery server. Please try again.") from exc
        except Exception as exc:
            logger.error("Unexpected error during email delivery to %s: error_type=%s details=%s", masked_to, type(exc).__name__, exc)
            raise EmailDeliveryError("An unexpected error occurred while sending verification email.") from exc

        logger.info("Successfully dispatched OTP email to %s via Brevo", masked_to)
        return True
