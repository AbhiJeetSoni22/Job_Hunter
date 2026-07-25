"""
app/cleanup.py

Manual/cron-invoked deletion of expired jobs that have no meaningful user
interaction (see JobService.cleanup_expired_jobs for the exact rule).

No scheduler or task queue exists in this project by design
(ARCHITECTURE.md §1: "No task queue. No scheduler."). This script is the
management-command entrypoint instead — run it by hand or wire it into an
external cron / CI scheduled job:

    python -m app.cleanup
    python -m app.cleanup --days 30

Uses its own fresh Session, same pattern as the background auto-score task
in routers/scraper.py — never reuses a request-scoped session.
"""

from __future__ import annotations

import argparse
import logging

from app.database import SessionLocal
from app.services.job_service import JobService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_cleanup(days: int = 30) -> int:
    """Delete eligible expired jobs older than `days`. Returns count deleted."""
    db = SessionLocal()
    try:
        return JobService(db).cleanup_expired_jobs(days=days)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Delete jobs expired for more than N days that were never "
            "applied to, interviewed for, or annotated with notes."
        )
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Expiry age threshold in days (default: 30)",
    )
    args = parser.parse_args()

    deleted = run_cleanup(days=args.days)
    logger.info("Cleanup complete — deleted %d job(s).", deleted)


if __name__ == "__main__":
    main()
