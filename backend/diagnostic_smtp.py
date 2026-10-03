import logging
import os
import smtplib
import socket
import ssl

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_tcp_connectivity(host: str, port: int) -> bool:
    logger.info(f"Attempting TCP connection to {host}:{port}")
    try:
        sock = socket.create_connection((host, port), timeout=15)
        logger.info(f"TCP connection established to {host}:{port}")
        sock.close()
        return True
    except socket.gaierror as e:
        logger.error(f"DNS failure for {host}:{port}: {e}")
        return False
    except TimeoutError as e:
        logger.error(f"Connection timeout to {host}:{port}: {e}")
        return False
    except ConnectionRefusedError as e:
        logger.error(f"Connection refused to {host}:{port}: {e}")
        return False
    except OSError as e:
        logger.error(f"Network error to {host}:{port}: {e}")
        return False


def test_smtp_587(host: str) -> bool:
    logger.info(f"Testing SMTP on {host}:587 (STARTTLS)")
    try:
        server = smtplib.SMTP(host, 587, timeout=15)
        logger.info("SMTP EHLO succeeded")
        server.ehlo()
        logger.info("Attempting STARTTLS")
        server.starttls()
        logger.info("STARTTLS succeeded")
        server.ehlo()

        username = os.environ.get("SMTP_USERNAME")
        password = os.environ.get("SMTP_PASSWORD")
        if username and password:
            logger.info("SMTP authentication started")
            try:
                server.login(username, password)
                logger.info("SMTP authentication succeeded")
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"Authentication failure: {e}")
        else:
            logger.info("Skipping SMTP authentication test (credentials not provided)")

        server.quit()
        return True
    except ssl.SSLError as e:
        logger.error(f"TLS failure on 587: {e}")
        return False
    except Exception as e:
        logger.error(f"SMTP error on 587: {e}")
        return False


def test_smtp_465(host: str) -> bool:
    logger.info(f"Testing SMTP on {host}:465 (SMTP_SSL)")
    try:
        server = smtplib.SMTP_SSL(host, 465, timeout=15)
        logger.info("SMTP EHLO/SSL succeeded")
        server.ehlo()

        username = os.environ.get("SMTP_USERNAME")
        password = os.environ.get("SMTP_PASSWORD")
        if username and password:
            logger.info("SMTP authentication started")
            try:
                server.login(username, password)
                logger.info("SMTP authentication succeeded")
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"Authentication failure: {e}")
        else:
            logger.info("Skipping SMTP authentication test (credentials not provided)")

        server.quit()
        return True
    except ssl.SSLError as e:
        logger.error(f"TLS failure on 465: {e}")
        return False
    except Exception as e:
        logger.error(f"SMTP error on 465: {e}")
        return False


def main() -> None:
    logger.info("Starting SMTP diagnostic tests")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")

    logger.info("--- Testing Port 587 ---")
    if test_tcp_connectivity(host, 587):
        test_smtp_587(host)
    else:
        logger.error(f"Failed TCP connection to {host}:587")

    logger.info("--- Testing Port 465 ---")
    if test_tcp_connectivity(host, 465):
        test_smtp_465(host)
    else:
        logger.error(f"Failed TCP connection to {host}:465")


if __name__ == "__main__":
    main()
