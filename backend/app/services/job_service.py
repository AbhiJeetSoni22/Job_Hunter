"""
Job service.

Owns all business logic for the `jobs` table:
  - Querying (list with filters/sort/pagination, single record)
  - Upserting scraped jobs (deduplication by URL)
  - Updating status and notes (application tracking)
  - Deleting jobs

Architecture rule (from ARCHITECTURE.md):
  Routers never query the database directly.
  This service is the only layer that touches the Job ORM model.

No HTTP concerns here — no Request, no Response, no status codes.
Raise ValueError for validation failures; raise LookupError for not-found.
Routers translate these into HTTP responses.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job import Job, JOB_STATUS_VALUES
from app.schemas.job import (
    JobListItem,
    JobResponse,
    JobUpdateRequest,
    JobUpdateResponse,
    JobUpsertData,
    PaginatedJobList,
)

logger = logging.getLogger(__name__)

# Allowed sort columns — whitelist prevents SQL injection via sort_by param
_SORT_COLUMN_MAP: dict[str, object] = {
    "created_at": Job.created_at,
    "posted_at": Job.posted_at,
    "match_score": Job.match_score,
}


class JobService:
    """
    Service for all job-related operations.

    Instantiated per request with an injected SQLAlchemy session:
        service = JobService(db)

    This class pattern (vs module-level functions) makes it easy to
    inject a test session without monkeypatching module globals.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── List jobs ──────────────────────────────────────────────────────────

    def list_jobs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        order: str = "desc",
        status: str | None = None,
        source: str | None = None,
        scored: bool | None = None,
        current_resume_uploaded_at: datetime | None = None,
    ) -> PaginatedJobList:
        """
        Return a paginated, filtered, sorted list of jobs.

        Args:
            page:       1-based page number.
            page_size:  Number of results per page (max 100).
            sort_by:    Column to sort by. One of: created_at, posted_at, match_score.
            order:      Sort direction: 'asc' or 'desc'.
            status:     Filter to jobs with this status. None = all statuses.
            source:     Filter to jobs from this source. None = all sources.
            scored:     True = only scored jobs, False = only unscored, None = all.
            current_resume_uploaded_at:
                        If provided, each JobListItem.needs_rescore is set
                        correctly. Pass resume.uploaded_at from the active resume.

        Returns:
            PaginatedJobList with jobs (list items, not full detail), total count,
            current page, and page size.

        Raises:
            ValueError: if sort_by or order value is not in the allowed set.
        """
        if sort_by not in _SORT_COLUMN_MAP:
            raise ValueError(
                f"Invalid sort_by '{sort_by}'. "
                f"Must be one of: {', '.join(_SORT_COLUMN_MAP)}"
            )
        if order not in ("asc", "desc"):
            raise ValueError("order must be 'asc' or 'desc'")

        stmt = select(Job)

        # ── Filters ────────────────────────────────────────────────────────
        if status is not None:
            stmt = stmt.where(Job.status == status)
        if source is not None:
            stmt = stmt.where(Job.source == source)
        if scored is True:
            stmt = stmt.where(Job.match_score.is_not(None))
        elif scored is False:
            stmt = stmt.where(Job.match_score.is_(None))

        # ── Count before pagination ────────────────────────────────────────
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = self._db.execute(count_stmt).scalar_one()

        # ── Sort ───────────────────────────────────────────────────────────
        sort_col = _SORT_COLUMN_MAP[sort_by]
        if sort_by == "match_score":
            # Unscored jobs always sort to the bottom regardless of direction
            order_expr = (
                sort_col.desc().nulls_last()  # type: ignore[union-attr]
                if order == "desc"
                else sort_col.asc().nulls_last()  # type: ignore[union-attr]
            )
        else:
            order_expr = (
                sort_col.desc()  # type: ignore[union-attr]
                if order == "desc"
                else sort_col.asc()  # type: ignore[union-attr]
            )
        stmt = stmt.order_by(order_expr)

        # ── Pagination ─────────────────────────────────────────────────────
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        rows = self._db.execute(stmt).scalars().all()

        # ── Build list items ───────────────────────────────────────────────
        items = [
            self._to_list_item(job, current_resume_uploaded_at)
            for job in rows
        ]

        return PaginatedJobList(
            jobs=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    # ── Get single job ─────────────────────────────────────────────────────

    def get_job(
        self,
        job_id: uuid.UUID,
        *,
        current_resume_uploaded_at: datetime | None = None,
    ) -> JobResponse:
        """
        Return a single job by ID.

        Args:
            job_id:                     UUID of the job to retrieve.
            current_resume_uploaded_at: Used to compute needs_rescore flag.

        Raises:
            LookupError: if no job with job_id exists.
        """
        job = self._get_or_raise(job_id)
        return self._to_response(job, current_resume_uploaded_at)

    # ── Update job (status / notes) ────────────────────────────────────────

    def update_job(
        self,
        job_id: uuid.UUID,
        update: "JobUpdateRequest",
    ) -> JobUpdateResponse:
        """
        Update status and/or notes on a job.

        Only status and notes are mutable by the user. All other fields
        are managed by scrapers or match_service.

        Args:
            job_id: UUID of the job to update.
            update: JobUpdateRequest with optional status and notes fields.

        Raises:
            LookupError:  if no job with job_id exists.
            ValueError:   if status is not in JOB_STATUS_VALUES
                          (also validated by Pydantic in the schema, but
                          double-checked here as a defensive measure).
        """
        job = self._get_or_raise(job_id)

        if update.status is not None:
            if update.status not in JOB_STATUS_VALUES:
                raise ValueError(
                    f"Invalid status '{update.status}'. "
                    f"Must be one of: {', '.join(JOB_STATUS_VALUES)}"
                )
            job.status = update.status

        if update.notes is not None:
            # Empty string clears notes — set to None so DB stores NULL
            job.notes = update.notes if update.notes.strip() else None

        job.updated_at = datetime.now(tz=timezone.utc)
        self._db.commit()
        self._db.refresh(job)

        logger.info("Updated job %s: status=%s", job_id, job.status)
        return JobUpdateResponse.model_validate(job)

    # ── Delete job ─────────────────────────────────────────────────────────

    def delete_job(self, job_id: uuid.UUID) -> None:
        """
        Permanently delete a job.

        Args:
            job_id: UUID of the job to delete.

        Raises:
            LookupError: if no job with job_id exists.
        """
        job = self._get_or_raise(job_id)
        self._db.delete(job)
        self._db.commit()
        logger.info("Deleted job %s", job_id)

    # ── Upsert scraped jobs ────────────────────────────────────────────────

    def upsert_jobs(self, jobs: list[JobUpsertData]) -> int:
        """
        Insert new jobs from a scraper run. Skip URLs that already exist.

        Uses INSERT ... ON CONFLICT DO NOTHING via individual inserts with
        IntegrityError catch. Simple and explicit — no SQLAlchemy dialect-
        specific upsert syntax needed at this scale.

        Args:
            jobs: List of normalised job data from a scraper.

        Returns:
            Number of new rows actually inserted (duplicates excluded).
        """
        inserted = 0

        for data in jobs:
            job = Job(
                title=data.title,
                company=data.company,
                company_url=data.company_url,
                description=data.description,
                url=data.url,
                source=data.source,
                location=data.location,
                posted_at=data.posted_at,
                # Defaults set by DB: id, status='saved', created_at, updated_at
            )
            self._db.add(job)
            try:
                self._db.flush()  # Detect constraint violation without full commit
                inserted += 1
            except IntegrityError:
                # URL already exists — skip this job, continue with others
                self._db.rollback()
                logger.debug("Skipped duplicate URL: %s", data.url)

        if inserted > 0:
            self._db.commit()

        logger.info("upsert_jobs: %d inserted, %d duplicates skipped",
                    inserted, len(jobs) - inserted)
        return inserted

    # ── Private helpers ────────────────────────────────────────────────────

    def _get_or_raise(self, job_id: uuid.UUID) -> Job:
        """Fetch a Job by primary key or raise LookupError."""
        job = self._db.get(Job, job_id)
        if job is None:
            raise LookupError(f"Job with id {job_id} not found")
        return job

    def _compute_needs_rescore(
        self,
        job: Job,
        current_resume_uploaded_at: datetime | None,
    ) -> bool:
        """
        Return True if job.resume_uploaded_at is older than the current resume.

        A job that has never been scored never needs a rescore — it just
        needs a first score.
        """
        if not job.is_scored:
            return False
        if current_resume_uploaded_at is None:
            return False
        if job.resume_uploaded_at is None:
            return True
        return job.resume_uploaded_at < current_resume_uploaded_at

    def _to_list_item(
        self,
        job: Job,
        current_resume_uploaded_at: datetime | None,
    ) -> JobListItem:
        """Convert a Job ORM instance to a JobListItem schema."""
        item = JobListItem.model_validate(job)
        item.needs_rescore = self._compute_needs_rescore(
            job, current_resume_uploaded_at
        )
        return item

    def _to_response(
        self,
        job: Job,
        current_resume_uploaded_at: datetime | None,
    ) -> JobResponse:
        """Convert a Job ORM instance to a full JobResponse schema."""
        response = JobResponse.model_validate(job)
        response.needs_rescore = self._compute_needs_rescore(
            job, current_resume_uploaded_at
        )
        return response