"""
Email service.

Handles sending transactional emails via Gmail SMTP.
Supports STARTTLS (port 587) and direct SSL (port 465) using standard Python smtplib.
Provides detailed diagnostic logging for cloud hosting environments (Render).
"""

import logging
import os
import smtplib
import socket
import ssl
from contextlib import suppress
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr

from app.config import get_settings

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 10.0


class EmailDeliveryError(Exception):
    """Raised when an email fails to deliver via SMTP."""
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
        raw_host = host if host is not None else settings.SMTP_HOST
        raw_port = port if port is not None else settings.SMTP_PORT
        raw_username = username if username is not None else settings.SMTP_USERNAME
        raw_password = password if password is not None else settings.SMTP_PASSWORD
        raw_from_email = from_email if from_email is not None else settings.SMTP_FROM_EMAIL

        self._host = raw_host.strip() if raw_host else "smtp.gmail.com"
        self._port = int(raw_port) if raw_port else 587
        self._username = raw_username.strip() if raw_username else ""
        # Strip whitespace/newlines and interstitial spaces common in Google App Passwords
        self._password = raw_password.strip().replace(" ", "") if raw_password else ""
        self._from_email = raw_from_email.strip() if raw_from_email else ""

    def send_otp_email(self, to_email: str, otp_code: str) -> bool:
        """
        Send a 6-digit verification code to the recipient's email address via Gmail SMTP.

        In production, requires valid SMTP credentials (SMTP_USERNAME and Google App Password).
        In development/test environments without credentials, logs the code safely
        so developers and local users can still complete the authentication flow.

        Raises:
            EmailDeliveryError: if connection, TLS, authentication, or dispatch fails.
        """
        settings = get_settings()
        app_env = os.environ.get("APP_ENV") or settings.APP_ENV

        is_configured = bool(self._password and self._username)

        logger.info(
            "SMTP DEBUG: host=%s port=%d username=%s password_configured=%s",
            self._host,
            self._port,
            self._username,
            is_configured,
        )

        if not is_configured:
            if app_env in {"production", "prod"}:
                logger.error("SMTP credentials (SMTP_USERNAME / SMTP_PASSWORD) are not configured in production!")
                raise EmailDeliveryError("Email service is not configured. Please contact support.")
            logger.info(
                "[DEV/TEST] SMTP credentials not set. Verification OTP for %s: %s",
                to_email,
                otp_code,
            )
            return True

        masked_to = _mask_email(to_email)
        subject = f"{otp_code} is your Job Hunter verification code"
        from_header = (
            self._from_email
            if self._from_email
            else (f"Job Hunter <{self._username}>" if self._username else "Job Hunter")
        )
        sender_addr = parseaddr(from_header)[1] or self._username

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
        message["To"] = to_email.strip()
        message["Date"] = formatdate(localtime=True)
        sender_domain = sender_addr.split("@")[-1] if "@" in sender_addr else "gmail.com"
        message["Message-ID"] = make_msgid(domain=sender_domain)

        message.attach(MIMEText(plain_text, "plain", "utf-8"))
        message.attach(MIMEText(html_content, "html", "utf-8"))

        # Pre-flight DNS diagnostic resolution (helps isolate Render DNS vs TCP connection issues)
        try:
            addr_info = socket.getaddrinfo(self._host, self._port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            resolved_ips = list(dict.fromkeys(r[4][0] for r in addr_info))
            logger.info("SMTP DEBUG: DNS resolved %s to %s", self._host, resolved_ips)
        except Exception as dns_exc:
            logger.warning("SMTP DEBUG: DNS resolution pre-check for %s failed: %s", self._host, dns_exc)

        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            if self._port == 465:
                # Direct SSL connection (port 465)
                logger.info("SMTP DEBUG: Connecting to %s:%d via SMTP_SSL (timeout=%.1fs)...", self._host, self._port, SMTP_TIMEOUT_SECONDS)
                server = smtplib.SMTP_SSL(self._host, self._port, timeout=SMTP_TIMEOUT_SECONDS)
                logger.info("SMTP DEBUG: TCP/SSL connection established to %s:%d", self._host, self._port)
                server.ehlo()
            else:
                # Standard connection with STARTTLS (port 587)
                logger.info("SMTP DEBUG: Connecting to %s:%d via SMTP (timeout=%.1fs)...", self._host, self._port, SMTP_TIMEOUT_SECONDS)
                server = smtplib.SMTP(self._host, self._port, timeout=SMTP_TIMEOUT_SECONDS)
                logger.info("SMTP DEBUG: TCP connection established to %s:%d", self._host, self._port)
                server.ehlo()
                logger.info("SMTP DEBUG: Establishing STARTTLS...")
                server.starttls()
                logger.info("SMTP DEBUG: STARTTLS handshake succeeded")
                server.ehlo()

            logger.info("SMTP DEBUG: Authenticating as %s...", self._username)
            server.login(self._username, self._password)
            logger.info("SMTP DEBUG: Authentication succeeded for user %s", self._username)

            logger.info("SMTP DEBUG: Sending MIME message to %s...", masked_to)
            server.send_message(message, from_addr=sender_addr, to_addrs=[to_email.strip()])
            logger.info("SMTP DEBUG: Message successfully accepted by SMTP server for %s", masked_to)

        except socket.gaierror as exc:
            logger.error("SMTP DNS resolution failed for %s:%d: [Errno %s] %s", self._host, self._port, getattr(exc, "errno", None), exc)
            raise EmailDeliveryError("Failed to connect to email delivery server. Please try again.") from exc
        except TimeoutError as exc:
            logger.error(
                "SMTP connection timed out to %s:%d after %.1fs: %s (Check if host environment blocks outbound SMTP port %d)",
                self._host,
                self._port,
                SMTP_TIMEOUT_SECONDS,
                exc,
                self._port,
            )
            raise EmailDeliveryError("Failed to connect to email delivery server. Please try again.") from exc
        except smtplib.SMTPAuthenticationError as exc:
            logger.error(
                "SMTP authentication failed for user %s: smtp_code=%s smtp_error=%s (Ensure SMTP_PASSWORD is a Google App Password, not standard account password)",
                self._username,
                getattr(exc, "smtp_code", None),
                getattr(exc, "smtp_error", None),
            )
            raise EmailDeliveryError("Failed to authenticate with email delivery server.") from exc
        except smtplib.SMTPRecipientsRefused as exc:
            logger.error("SMTP recipient refused: %s", masked_to)
            raise EmailDeliveryError("Recipient email address was rejected by mail server.") from exc
        except ssl.SSLError as exc:
            logger.error("SMTP TLS handshake failure with %s:%d: %s", self._host, self._port, exc)
            raise EmailDeliveryError("Failed to establish secure connection to email delivery server.") from exc
        except (ConnectionRefusedError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, OSError) as exc:
            logger.error(
                "SMTP connection failure to %s:%d: error_type=%s errno=%s details=%s",
                self._host,
                self._port,
                type(exc).__name__,
                getattr(exc, "errno", None),
                exc,
            )
            raise EmailDeliveryError("Failed to connect to email delivery server. Please try again.") from exc
        except smtplib.SMTPException as exc:
            logger.error("SMTP delivery failure to %s: error_type=%s details=%s", masked_to, type(exc).__name__, exc)
            raise EmailDeliveryError("Failed to dispatch verification email. Please try again.") from exc
        except Exception as exc:
            logger.error("Unexpected error during email delivery to %s: error_type=%s details=%s", masked_to, type(exc).__name__, exc)
            raise EmailDeliveryError("An unexpected error occurred while sending verification email.") from exc
        finally:
            if server is not None:
                with suppress(Exception):
                    server.quit()

        logger.info("Successfully dispatched OTP email to %s via Gmail SMTP", masked_to)
        return True
