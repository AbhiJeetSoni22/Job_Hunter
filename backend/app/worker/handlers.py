"""
Task handlers for the background worker.

Dispatches claimed tasks to existing domain services:
  - ScraperService: scraping, ScrapeRun logging, auto-scoring.
  - JobService: stale/unscored job discovery.
  - match_service: Gemini matching.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.task import Task
from app.services.job_service import JobService
from app.services.scraper_service import ScraperService

logger = logging.getLogger(__name__)


def handle_scrape(task: Task, db: Session) -> dict[str, Any]:
    """
    Execute full multi-source job scraping.

    Payload options:
        - auto_score (bool): whether newly discovered jobs should be auto-scored.
        - user_id (str): optional user to score against if auto_score=True.
    """
    logger.info("Executing scrape task id=%s", task.id)
    service = ScraperService(db)
    summary, new_job_ids = service.run_all()

    auto_score = task.payload.get("auto_score", True)
    user_id = task.user_id or task.payload.get("user_id")

    scoring_run_id = None
    if auto_score and user_id and new_job_ids:
        uid = uuid.UUID(str(user_id))
        scoring_run = service.start_scoring_run(len(new_job_ids), user_id=uid)
        scoring_run_id = str(scoring_run.id)
        service.run_auto_score(
            new_job_ids,
            scoring_run_id=scoring_run.id,
            user_id=uid,
            force=False,
        )

    return {
        "total_new": summary.total_new,
        "runs": [
            {
                "source": r.source,
                "jobs_found": r.jobs_found,
                "jobs_new": r.jobs_new,
                "error": r.error,
            }
            for r in summary.runs
        ],
        "new_job_ids": [str(jid) for jid in new_job_ids],
        "scoring_run_id": scoring_run_id,
    }


def handle_scoring(task: Task, db: Session) -> dict[str, Any]:
    """
    Score specific jobs against a user's active resume.

    Payload options:
        - job_ids (list[str]): list of job UUID strings.
        - scoring_run_id (str): optional ScoringRun UUID string.
        - force (bool): whether to bypass cached scores.
    """
    job_ids = task.payload.get("job_ids", [])
    if not job_ids:
        return {"total_jobs": 0, "status": "completed", "message": "No job IDs provided"}

    user_id = task.user_id or task.payload.get("user_id")
    if not user_id:
        raise ValueError("user_id is required for scoring tasks")

    uid = uuid.UUID(str(user_id))
    scoring_run_id_raw = task.payload.get("scoring_run_id")
    scoring_run_id = uuid.UUID(str(scoring_run_id_raw)) if scoring_run_id_raw else None
    force = bool(task.payload.get("force", False))

    service = ScraperService(db, user_id=uid)
    service.run_auto_score(
        job_ids,
        scoring_run_id=scoring_run_id,
        user_id=uid,
        force=force,
    )

    return {
        "total_jobs": len(job_ids),
        "scoring_run_id": str(scoring_run_id) if scoring_run_id else None,
        "user_id": str(uid),
    }


def handle_bulk_score(task: Task, db: Session) -> dict[str, Any]:
    """
    Find unscored or stale jobs for a user and score them.

    Payload options:
        - include_stale (bool): whether to rescore stale jobs (default True).
        - limit (int): maximum jobs to score in this batch (default 100).
        - scoring_run_id (str): optional pre-created ScoringRun ID.
    """
    user_id = task.user_id or task.payload.get("user_id")
    if not user_id:
        raise ValueError("user_id is required for bulk scoring tasks")

    uid = uuid.UUID(str(user_id))
    include_stale = bool(task.payload.get("include_stale", True))
    limit = int(task.payload.get("limit", 100))

    job_service = JobService(db, user_id=uid)
    eligible_ids = job_service.find_unscored_and_stale_job_ids(
        user_id=uid,
        include_stale=include_stale,
        limit=limit,
    )

    job_id_strs = [str(jid) for jid in eligible_ids]
    if not job_id_strs:
        return {
            "total_eligible": 0,
            "status": "completed",
            "message": "All jobs are already scored and up-to-date.",
        }

    scraper_service = ScraperService(db, user_id=uid)
    scoring_run_id_raw = task.payload.get("scoring_run_id")
    if scoring_run_id_raw:
        scoring_run_id = uuid.UUID(str(scoring_run_id_raw))
    else:
        run = scraper_service.start_scoring_run(total_jobs=len(job_id_strs), user_id=uid)
        scoring_run_id = run.id

    scraper_service.run_auto_score(
        job_id_strs,
        scoring_run_id=scoring_run_id,
        user_id=uid,
        force=True,
    )

    return {
        "total_eligible": len(job_id_strs),
        "scoring_run_id": str(scoring_run_id),
        "user_id": str(uid),
    }


# Map task types to handler functions
TASK_HANDLERS = {
    "scrape": handle_scrape,
    "scoring": handle_scoring,
    "bulk_score": handle_bulk_score,
}
