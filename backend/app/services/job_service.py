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
from datetime import datetime, timezone

from sqlalchemy import asc, desc, func, select
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
    ) -> PaginatedJobList:
        if sort_by not in VALID_SORT_COLUMNS:
            raise ValueError(
                f"Invalid sort_by '{sort_by}'. Must be one of: {', '.join(sorted(VALID_SORT_COLUMNS))}"
            )
        if order not in VALID_ORDER:
            raise ValueError(f"Invalid order '{order}'. Must be 'asc' or 'desc'.")

        query = select(Job)

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

    def upsert_jobs(self, jobs: list[JobUpsertData]) -> int:
        """
        Insert new jobs; skip duplicates by URL.
        Returns count of newly inserted rows.
        """
        new_count = 0
        for data in jobs:
            exists = self.db.scalar(
                select(func.count()).where(Job.url == data.url)
            )
            if exists:
                logger.debug("upsert skip duplicate url=%s", data.url)
                continue

            job = Job(
                id=str(uuid.uuid4()),
                title=data.title,
                company=data.company,
                company_url=data.company_url,
                description=data.description,
                url=data.url,
                source=data.source,
                location=data.location,
                posted_at=data.posted_at,
                status="saved",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(job)
            new_count += 1
            logger.debug("upsert new job url=%s", data.url)

        self.db.commit()
        logger.info("upsert complete new=%d", new_count)
        return new_count

    # ── Private helpers ───────────────────────────────────────────────────

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
            posted_at=job.posted_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )