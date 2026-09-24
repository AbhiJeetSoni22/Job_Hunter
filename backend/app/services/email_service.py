"""
Email service.

Handles sending transactional emails via Gmail SMTP using STARTTLS.
Uses standard Python smtplib and email.mime libraries.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when an email fails to deliver via SMTP."""
    pass


class EmailService:
    """Service for dispatching transactional emails via Gmail SMTP."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
    ) -> None:
        settings = get_settings()
        self._host = host if host is not None else settings.SMTP_HOST
        self._port = port if port is not None else settings.SMTP_PORT
        self._username = username if username is not None else settings.SMTP_USERNAME
        self._password = password if password is not None else settings.SMTP_PASSWORD
        self._from_email = from_email if from_email is not None else settings.SMTP_FROM_EMAIL

    def send_otp_email(self, to_email: str, otp_code: str) -> bool:
        """
        Send a 6-digit verification code to the recipient's email address via Gmail SMTP.

        In production, requires valid SMTP credentials.
        In development/test environments without credentials, logs the code safely
        so developers and local users can still complete the authentication flow.

        Raises:
            EmailDeliveryError: if connection, TLS, authentication, or dispatch fails.
        """
        settings = get_settings()
        import os
        app_env = os.environ.get("APP_ENV") or settings.APP_ENV

        is_configured = bool(
            self._password
            and self._password.strip()
            and self._username
            and self._username.strip()
        )

        logger.info(
            "EmailService dispatch check: host=%s, port=%s, username=%s, configured=%s",
            self._host,
            self._port,
            self._username,
            is_configured,
        )

        if not is_configured:
            if app_env in {"production", "prod"}:
                logger.error("SMTP credentials are not configured in production!")
                raise EmailDeliveryError("Email service is not configured. Please contact support.")
            logger.info(
                "[DEV/TEST] SMTP credentials not set. Verification OTP for %s: %s",
                to_email,
                otp_code,
            )
            return True

        subject = f"{otp_code} is your Job Hunter verification code"
        from_header = (
            self._from_email.strip()
            if self._from_email and self._from_email.strip()
            else (f"Job Hunter <{self._username.strip()}>" if self._username else "Job Hunter")
        )
        sender_addr = parseaddr(from_header)[1] or self._username.strip()

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

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = from_header
        message["To"] = to_email
        message["Date"] = formatdate(localtime=True)
        sender_domain = sender_addr.split("@")[-1] if "@" in sender_addr else "gmail.com"
        message["Message-ID"] = make_msgid(domain=sender_domain)

        message.attach(MIMEText(plain_text, "plain", "utf-8"))
        message.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            with smtplib.SMTP(self._host, self._port, timeout=10.0) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self._username, self._password)
                server.send_message(message, from_addr=sender_addr, to_addrs=[to_email])
        except smtplib.SMTPAuthenticationError as exc:
            logger.error("SMTP authentication failed for user %s: code=%s", self._username, exc.smtp_code)
            raise EmailDeliveryError("Failed to authenticate with email delivery server.") from exc
        except smtplib.SMTPRecipientsRefused as exc:
            logger.error("SMTP recipient refused: %s", to_email)
            raise EmailDeliveryError("Recipient email address was rejected by mail server.") from exc
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError) as exc:
            logger.error("SMTP connection failure to %s:%s: %s", self._host, self._port, exc.__class__.__name__)
            raise EmailDeliveryError("Failed to connect to email delivery server. Please try again.") from exc
        except smtplib.SMTPException as exc:
            logger.error("SMTP delivery failure to %s: %s", to_email, exc.__class__.__name__)
            raise EmailDeliveryError("Failed to dispatch verification email. Please try again.") from exc
        except Exception as exc:
            logger.error("Unexpected error during email delivery to %s: %s", to_email, exc.__class__.__name__)
            raise EmailDeliveryError("An unexpected error occurred while sending verification email.") from exc

        logger.info("Successfully dispatched OTP email to %s via Gmail SMTP", to_email)
        return True
