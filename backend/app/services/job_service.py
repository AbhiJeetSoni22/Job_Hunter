"""
services/job_service.py

All business logic for job CRUD, deduplication, and stale-score detection.

Multi-user architecture:
  - Job is a global scraped listing deduplicated by canonical URL.
  - UserJob holds user-specific state: status, notes, match_score, missing_skills,
    match_summary, matched_at, resume_uploaded_at.
  - delete_job removes ONLY the user's UserJob relationship, preserving the global Job.
  - All listing, querying, updating, and scoring are scoped by user_id.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from typing import Any, cast

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.user_job import UserJob
from app.schemas.job import (
    JobListItem,
    JobResponse,
    JobUpdateRequest,
    JobUpdateResponse,
    JobUpsertData,
    PaginatedJobList,
)
from app.services.match_service import recommendation_label

logger = logging.getLogger(__name__)

VALID_SORT_COLUMNS = {"created_at", "posted_at", "match_score"}
VALID_ORDER = {"asc", "desc"}
VALID_STATUSES = {"saved", "applied", "interview", "offer", "rejected"}

# Job lifecycle (docs/ARCHITECTURE.md §7 Data Flow — Job Lifecycle)
EXPIRE_AFTER_MISSING_SYNCS = 2


class JobService:
    def __init__(self, db: Session, user_id: uuid.UUID | str | None = None) -> None:
        self.db = db
        self.user_id = user_id

    def _resolve_user_id(self, user_id: uuid.UUID | str | None) -> uuid.UUID:
        uid = user_id or self.user_id
        if not uid:
            raise ValueError("user_id is required for user-scoped job operations")
        return uuid.UUID(str(uid)) if not isinstance(uid, uuid.UUID) else uid

    # ── List ──────────────────────────────────────────────────────────────

    def list_jobs(
        self,
        user_id: uuid.UUID | None = None,
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

        uid = self._resolve_user_id(user_id)
        query = (
            select(Job, UserJob)
            .outerjoin(
                UserJob,
                and_(UserJob.job_id == Job.id, UserJob.user_id == uid),
            )
        )

        if not include_expired:
            query = query.where(Job.expired_at.is_(None))
        if status is not None:
            query = query.where(func.coalesce(UserJob.status, "saved") == status)
        if source is not None:
            query = query.where(Job.source == source)
        if scored is True:
            query = query.where(UserJob.match_score.isnot(None))
        if scored is False:
            query = query.where(or_(UserJob.id.is_(None), UserJob.match_score.is_(None)))

        if sort_by == "match_score":
            sort_col = UserJob.match_score
        else:
            sort_col = getattr(Job, sort_by)

        query = query.order_by(
            desc(sort_col).nulls_last() if order == "desc" else asc(sort_col).nulls_last()
        )

        total = self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        offset = (page - 1) * page_size
        rows = self.db.execute(query.offset(offset).limit(page_size)).all()

        items = [
            self._to_list_item(job, user_job, current_resume_uploaded_at)
            for job, user_job in rows
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
        user_id: uuid.UUID | None = None,
        current_resume_uploaded_at: datetime | None = None,
    ) -> JobResponse:
        uid = self._resolve_user_id(user_id)
        job = self.db.get(Job, str(job_id))
        if job is None:
            raise LookupError(f"Job {job_id} not found")
        user_job = self.db.scalar(
            select(UserJob).where(
                UserJob.job_id == job.id,
                UserJob.user_id == uid,
            )
        )
        return self._to_response(job, user_job, current_resume_uploaded_at)

    # ── Update ────────────────────────────────────────────────────────────

    def update_job(
        self,
        job_id: uuid.UUID,
        body: JobUpdateRequest,
        user_id: uuid.UUID | None = None,
    ) -> JobUpdateResponse:
        uid = self._resolve_user_id(user_id)
        job = self.db.get(Job, str(job_id))
        if job is None:
            raise LookupError(f"Job {job_id} not found")

        if body.status is not None:
            if body.status not in VALID_STATUSES:
                raise ValueError(
                    f"Invalid status '{body.status}'. "
                    f"Must be one of: {', '.join(sorted(VALID_STATUSES))}"
                )

        user_job = self.db.scalar(
            select(UserJob).where(
                UserJob.job_id == job.id,
                UserJob.user_id == uid,
            )
        )
        now = datetime.now(UTC)
        if user_job is None:
            user_job = UserJob(
                id=uuid.uuid4(),
                user_id=uid,
                job_id=job.id,
                status=body.status if body.status is not None else "saved",
                notes=body.notes,
                created_at=now,
                updated_at=now,
            )
            self.db.add(user_job)
        else:
            if body.status is not None:
                user_job.status = body.status
            if body.notes is not None:
                user_job.notes = body.notes
            user_job.updated_at = now

        self.db.commit()
        self.db.refresh(user_job)

        return JobUpdateResponse(
            id=job.id,
            status=user_job.status,
            notes=user_job.notes,
        )

    # ── Delete ────────────────────────────────────────────────────────────

    def delete_job(self, job_id: uuid.UUID, user_id: uuid.UUID | None = None) -> None:
        """
        Delete the user's relationship/data for this job.

        Never deletes the global Job record, so other users can still access it.
        """
        uid = self._resolve_user_id(user_id)
        job = self.db.get(Job, str(job_id))
        if job is None:
            raise LookupError(f"Job {job_id} not found")

        user_job = self.db.scalar(
            select(UserJob).where(
                UserJob.job_id == job.id,
                UserJob.user_id == uid,
            )
        )
        if user_job is not None:
            self.db.delete(user_job)
            self.db.commit()

    # ── Upsert (called by scraper_service) ────────────────────────────────

    def upsert_jobs(
        self,
        jobs: list[JobUpsertData],
        new_job_ids: list[str] | None = None,
        source: str | None = None,
    ) -> int:
        """
        Insert new global jobs; mark existing jobs (by URL) as seen; skip nothing.
        """
        now = datetime.now(UTC)
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
                last_seen_at=now,
                missing_sync_count=0,
                created_at=now,
                updated_at=now,
            )
            self.db.add(job)
            new_count += 1
            if new_job_ids is not None:
                new_job_ids.append(str(job.id))
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
        meaningful user interaction across ANY user.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(Job)
            .where(
                Job.expired_at.isnot(None),
                Job.expired_at <= cutoff,
                ~Job.user_jobs.any(
                    or_(
                        UserJob.status != "saved",
                        and_(UserJob.notes.isnot(None), UserJob.notes != ""),
                    )
                ),
            )
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
            job.expired_at = cast(datetime | None, None)

    def _age_missing_jobs(
        self,
        source: str,
        seen_urls: set[str],
        now: datetime,
    ) -> None:
        """Bump missing_sync_count for every active job of `source` not in batch."""
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
        user_job: UserJob | None,
        current_resume_uploaded_at: datetime | None,
    ) -> bool:
        if user_job is None or user_job.match_score is None:
            return False
        if current_resume_uploaded_at is None:
            return False
        return user_job.resume_uploaded_at != current_resume_uploaded_at

    def _to_list_item(
        self,
        job: Job,
        user_job: UserJob | None,
        current_resume_uploaded_at: datetime | None,
    ) -> JobListItem:
        status = user_job.status if user_job else "saved"
        match_score = user_job.match_score if user_job else None
        return JobListItem(
            id=job.id,
            title=job.title,
            company=job.company,
            company_url=job.company_url,
            url=job.url,
            source=job.source,
            location=job.location,
            status=status,
            match_score=match_score,
            needs_rescore=self._compute_needs_rescore(user_job, current_resume_uploaded_at),
            recommendation_label=recommendation_label(match_score),
            expired_at=job.expired_at,
            posted_at=job.posted_at,
            created_at=job.created_at,
            updated_at=user_job.updated_at if user_job else job.updated_at,
        )

    def _to_response(
        self,
        job: Job,
        user_job: UserJob | None,
        current_resume_uploaded_at: datetime | None,
    ) -> JobResponse:
        status = user_job.status if user_job else "saved"
        notes = user_job.notes if user_job else None
        match_score = user_job.match_score if user_job else None
        missing_skills = user_job.missing_skills if user_job else None
        match_summary = user_job.match_summary if user_job else None
        matched_at = user_job.matched_at if user_job else None
        resume_uploaded_at = user_job.resume_uploaded_at if user_job else None
        return JobResponse(
            id=job.id,
            title=job.title,
            company=job.company,
            company_url=job.company_url,
            description=job.description,
            url=job.url,
            source=job.source,
            location=job.location,
            status=status,
            notes=notes,
            match_score=match_score,
            missing_skills=missing_skills,
            match_summary=match_summary,
            matched_at=matched_at,
            needs_rescore=self._compute_needs_rescore(user_job, current_resume_uploaded_at),
            recommendation_label=recommendation_label(match_score),
            resume_uploaded_at=resume_uploaded_at,
            expired_at=job.expired_at,
            posted_at=job.posted_at,
            created_at=job.created_at,
            updated_at=user_job.updated_at if user_job else job.updated_at,
        )