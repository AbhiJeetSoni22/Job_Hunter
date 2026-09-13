"""
services/job_service.py

All business logic for job CRUD, deduplication, and stale-score detection.

Changes in Phase 2D:
  - list_jobs() and get_job() accept optional current_resume_uploaded_at
  - needs_rescore computed and attached to every JobListItem and JobResponse
  - needs_rescore = True when match_score exists AND resume_uploaded_at != current resume
  - needs_rescore = False when no score yet, or score matches current resume
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.schemas.job import (
    JobListItem,
    JobResponse,
    JobUpdateRequest,
    JobUpdateResponse,
    JobUpsertData,
    PaginatedJobList,
)

logger = logging.getLogger(__name__)

VALID_SORT_COLUMNS = {"created_at", "posted_at", "match_score"}
VALID_ORDER = {"asc", "desc"}
VALID_STATUSES = {"saved", "applied", "interview", "offer", "rejected"}

# Job lifecycle (docs/ARCHITECTURE.md §7 Data Flow — Job Lifecycle)
EXPIRE_AFTER_MISSING_SYNCS = 2


class JobService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── List ──────────────────────────────────────────────────────────────

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
        include_expired: bool = False,
    ) -> PaginatedJobList:
        if sort_by not in VALID_SORT_COLUMNS:
            raise ValueError(
                f"Invalid sort_by '{sort_by}'. Must be one of: {', '.join(sorted(VALID_SORT_COLUMNS))}"
            )
        if order not in VALID_ORDER:
            raise ValueError(f"Invalid order '{order}'. Must be 'asc' or 'desc'.")

        query = select(Job)

        if not include_expired:
            query = query.where(Job.expired_at.is_(None))
        if status is not None:
            query = query.where(Job.status == status)
        if source is not None:
            query = query.where(Job.source == source)
        if scored is True:
            query = query.where(Job.match_score.isnot(None))
        if scored is False:
            query = query.where(Job.match_score.is_(None))

        sort_col = getattr(Job, sort_by)
        query = query.order_by(
            desc(sort_col).nulls_last() if order == "desc" else asc(sort_col).nulls_last()
        )

        total = self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        offset = (page - 1) * page_size
        rows = self.db.scalars(query.offset(offset).limit(page_size)).all()

        items = [
            self._to_list_item(job, current_resume_uploaded_at)
            for job in rows
        ]

        return PaginatedJobList(
            jobs=items,
            total=total or 0,
            page=page,
            page_size=page_size,
        )

    # ── Detail ────────────────────────────────────────────────────────────

    def get_job(
        self,
        job_id: uuid.UUID,
        current_resume_uploaded_at: datetime | None = None,
    ) -> JobResponse:
        job = self.db.get(Job, str(job_id))
        if job is None:
            raise LookupError(f"Job {job_id} not found")
        return self._to_response(job, current_resume_uploaded_at)

    # ── Update ────────────────────────────────────────────────────────────

    def update_job(
        self,
        job_id: uuid.UUID,
        body: JobUpdateRequest,
    ) -> JobUpdateResponse:
        job = self.db.get(Job, str(job_id))
        if job is None:
            raise LookupError(f"Job {job_id} not found")

        if body.status is not None:
            if body.status not in VALID_STATUSES:
                raise ValueError(
                    f"Invalid status '{body.status}'. "
                    f"Must be one of: {', '.join(sorted(VALID_STATUSES))}"
                )
            job.status = body.status

        if body.notes is not None:
            job.notes = body.notes

        job.updated_at = datetime.now(timezone.utc)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return JobUpdateResponse.model_validate(job)

    # ── Delete ────────────────────────────────────────────────────────────

    def delete_job(self, job_id: uuid.UUID) -> None:
        job = self.db.get(Job, str(job_id))
        if job is None:
            raise LookupError(f"Job {job_id} not found")
        self.db.delete(job)
        self.db.commit()

    # ── Upsert (called by scraper_service) ────────────────────────────────

    def upsert_jobs(
        self,
        jobs: list[JobUpsertData],
        new_job_ids: list[str] | None = None,
        source: str | None = None,
    ) -> int:
        """
        Insert new jobs; mark existing jobs (by URL) as seen; skip nothing.

        Also drives job-lifecycle tracking (last_seen_at, missing_sync_count,
        expired_at) for every OTHER active job belonging to the same source
        that was NOT in this batch — those jobs disappeared from the source
        during this sync. One source's sync never touches another source's
        jobs (`Job.source == source` scopes every lifecycle query).

        Args:
            jobs: normalised job data for ONE source's sync (as produced by
                a single scraper's run()).
            new_job_ids: if provided, ids of newly inserted jobs are appended.
            source: the source this batch belongs to. Required to detect
                missing jobs when `jobs` is empty (a scraper that found
                nothing still needs its existing jobs aged). Inferred from
                the batch when omitted and non-empty, for backward
                compatibility with existing callers/tests.

        Returns:
            Count of newly inserted rows (unchanged contract).

        Efficient by construction: one query to bulk-load existing rows for
        this batch's URLs, one query to bulk-load this source's active jobs
        missing from the batch. No per-job queries — no N+1.
        """
        now = datetime.now(timezone.utc)
        batch_source = source or (jobs[0].source if jobs else None)

        urls = [data.url for data in jobs]
        existing_by_url: dict[str, Job] = {}
        if urls:
            existing_rows = self.db.scalars(
                select(Job).where(Job.url.in_(urls))
            ).all()
            existing_by_url = {job.url: job for job in existing_rows}

        seen_urls: set[str] = set()
        new_count = 0

        for data in jobs:
            seen_urls.add(data.url)
            existing = existing_by_url.get(data.url)

            if existing is not None:
                self._mark_seen(existing, now)
                logger.debug("upsert seen existing url=%s", data.url)
                continue

            job = Job(
                id=uuid.uuid4(),
                title=data.title,
                company=data.company,
                company_url=data.company_url,
                description=data.description,
                url=data.url,
                source=data.source,
                location=data.location,
                posted_at=data.posted_at,
                status="saved",
                last_seen_at=now,
                missing_sync_count=0,
                created_at=now,
                updated_at=now,
            )
            self.db.add(job)
            new_count += 1
            if new_job_ids is not None:
                new_job_ids.append(job.id)
            logger.debug("upsert new job url=%s", data.url)

        if batch_source is not None:
            self._age_missing_jobs(batch_source, seen_urls, now)

        self.db.commit()
        logger.info("upsert complete new=%d", new_count)
        return new_count

    # ── Cleanup (called by app/cleanup.py) ─────────────────────────────────

    def cleanup_expired_jobs(self, *, days: int = 30) -> int:
        """
        Permanently delete expired jobs older than `days` with no
        meaningful user interaction.

        Eligible for deletion only when ALL of:
          - expired_at is set and at least `days` days in the past
          - status is still "saved" (user never applied/interviewed/etc.)
          - notes is empty (user never annotated it)

        Anything the user acted on (status changed, or notes added) is
        kept forever, regardless of expiry age.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = select(Job).where(
            Job.expired_at.isnot(None),
            Job.expired_at <= cutoff,
            Job.status == "saved",
            or_(Job.notes.is_(None), Job.notes == ""),
        )
        rows = self.db.scalars(stmt).all()
        deleted = len(rows)

        for job in rows:
            self.db.delete(job)
        self.db.commit()

        logger.info("cleanup_expired_jobs deleted=%d cutoff_days=%d", deleted, days)
        return deleted

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _mark_seen(job: Job, now: datetime) -> None:
        """Reset lifecycle state for a job whose URL appeared in this sync."""
        job.last_seen_at = now
        job.missing_sync_count = 0
        if job.expired_at is not None:
            job.expired_at = None  # reappeared — active again

    def _age_missing_jobs(
        self,
        source: str,
        seen_urls: set[str],
        now: datetime,
    ) -> None:
        """
        Bump missing_sync_count for every active job of `source` that was
        NOT in this sync's batch. Expires jobs that hit the threshold.

        Scoped strictly to `source` — a sync of one source never marks
        another source's jobs as missing/expired.
        """
        stmt = select(Job).where(
            Job.source == source,
            Job.expired_at.is_(None),
        )
        if seen_urls:
            stmt = stmt.where(Job.url.notin_(seen_urls))

        rows = self.db.scalars(stmt).all()
        for job in rows:
            job.missing_sync_count += 1
            if job.missing_sync_count >= EXPIRE_AFTER_MISSING_SYNCS:
                job.expired_at = now

    @staticmethod
    def _compute_needs_rescore(
        job: Job,
        current_resume_uploaded_at: datetime | None,
    ) -> bool:
        """
        True only when:
          - a score already exists (match_score is not None)
          - AND the resume used for that score differs from the current resume
        False when:
          - no score yet (nothing to re-score)
          - no resume uploaded (can't compare)
          - score was computed against the current resume
        """
        if job.match_score is None:
            return False
        if current_resume_uploaded_at is None:
            return False
        return job.resume_uploaded_at != current_resume_uploaded_at

    def _to_list_item(
        self,
        job: Job,
        current_resume_uploaded_at: datetime | None,
    ) -> JobListItem:
        return JobListItem(
            id=job.id,
            title=job.title,
            company=job.company,
            company_url=job.company_url,
            url=job.url,
            source=job.source,
            location=job.location,
            status=job.status,
            match_score=job.match_score,
            needs_rescore=self._compute_needs_rescore(job, current_resume_uploaded_at),
            expired_at=job.expired_at,
            posted_at=job.posted_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def _to_response(
        self,
        job: Job,
        current_resume_uploaded_at: datetime | None,
    ) -> JobResponse:
        return JobResponse(
            id=job.id,
            title=job.title,
            company=job.company,
            company_url=job.company_url,
            description=job.description,
            url=job.url,
            source=job.source,
            location=job.location,
            status=job.status,
            notes=job.notes,
            match_score=job.match_score,
            missing_skills=job.missing_skills,
            match_summary=job.match_summary,
            matched_at=job.matched_at,
            needs_rescore=self._compute_needs_rescore(job, current_resume_uploaded_at),
            resume_uploaded_at=job.resume_uploaded_at,
            expired_at=job.expired_at,
            posted_at=job.posted_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )