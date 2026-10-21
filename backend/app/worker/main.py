"""
Executable entry point for the background task worker.

Usage:
    python -m app.worker.main
    python -m app.worker.main --poll-interval 1.0 --once
"""

import argparse
import logging
import re
import sys

from app.config import get_settings
from app.worker.worker import BackgroundWorker


def sanitize_error_message(message: str) -> str:
    """
    Remove sensitive credentials such as database passwords or API keys from error messages.
    """
    sanitized = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", message)
    sanitized = re.sub(
        r"(password|secret|key|token)=([^\s,;]+)",
        r"\1=***",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Job Hunter Background Task Worker")
    parser.add_argument("--worker-id", type=str, default=None, help="Explicit worker identifier")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument("--lease-seconds", type=int, default=300, help="Lease timeout duration in seconds")
    parser.add_argument("--once", action="store_true", help="Process at most one task and exit")
    parser.add_argument(
        "--drain",
        action="store_true",
        help="Drain all currently eligible queued tasks and exit cleanly with code 0",
    )
    parser.add_argument(
        "--max-duration-seconds",
        type=float,
        default=300.0,
        help="Maximum drain duration in seconds before stopping task claims (default: 300.0)",
    )

    args = parser.parse_args(argv)

    try:
        settings = get_settings()
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    except Exception as init_exc:
        logging.basicConfig(level=logging.INFO)
        sanitized_msg = sanitize_error_message(str(init_exc))
        logging.getLogger("app.worker").critical(
            "Fatal worker initialization error: %s", sanitized_msg
        )
        sys.exit(1)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] (worker) %(name)s: %(message)s",
    )

    try:
        worker = BackgroundWorker(
            worker_id=args.worker_id,
            poll_interval=args.poll_interval,
            lease_seconds=args.lease_seconds,
        )

        if args.drain:
            worker.run_drain(max_duration_seconds=args.max_duration_seconds)
            sys.exit(0)
        elif args.once:
            processed = worker.run_once()
            sys.exit(0 if processed else 1)
        else:
            worker.run()
    except SystemExit:
        raise
    except Exception as exc:
        sanitized_msg = sanitize_error_message(str(exc))
        logging.getLogger("app.worker").critical(
            "Fatal error in worker execution: %s", sanitized_msg
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

