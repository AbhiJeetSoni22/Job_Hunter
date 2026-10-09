"""
Executable entry point for the background task worker.

Usage:
    python -m app.worker.main
    python -m app.worker.main --poll-interval 1.0 --once
"""

import argparse
import logging
import sys

from app.config import get_settings
from app.worker.worker import BackgroundWorker


def main() -> None:
    parser = argparse.ArgumentParser(description="Job Hunter Background Task Worker")
    parser.add_argument("--worker-id", type=str, default=None, help="Explicit worker identifier")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument("--lease-seconds", type=int, default=300, help="Lease timeout duration in seconds")
    parser.add_argument("--once", action="store_true", help="Process at most one task and exit")

    args = parser.parse_args()

    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] (worker) %(name)s: %(message)s",
    )

    worker = BackgroundWorker(
        worker_id=args.worker_id,
        poll_interval=args.poll_interval,
        lease_seconds=args.lease_seconds,
    )

    if args.once:
        processed = worker.run_once()
        sys.exit(0 if processed else 1)
    else:
        worker.run()


if __name__ == "__main__":
    main()
