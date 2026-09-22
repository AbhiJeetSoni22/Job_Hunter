"""
services/dashboard_service.py

Aggregate statistics for the AI-powered recommendation dashboard.

Multi-user architecture:
  - Scoped strictly to the authenticated user's UserJob records.
  - total_jobs reports all globally active scraped jobs.
  - scored_jobs, scores, applications_submitted, quality_breakdown, and top_matches
    are all derived strictly from the authenticated user's UserJob entries.
"""

from __future__ import annotations

import time
import uuid

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.user_job import UserJob
from app.schemas.dashboard import DashboardStats, MatchQualityBreakdown, TopMatchItem
from app.services.match_service import recommendation_label

TOP_MATCHES_LIMIT = 5

# Match-quality tier thresholds (Feature 2 — distinct from the
# recommendation-label thresholds used by Feature 5).
EXCELLENT_MIN = 90
GOOD_MIN = 75
POSSIBLE_MIN = 60


class DashboardService:
    def __init__(self, db: Session, user_id: uuid.UUID | str | None = None) -> None:
        self.db = db
        self.user_id = user_id

    def _resolve_user_id(self, user_id: uuid.UUID | str | None) -> uuid.UUID:
        uid = user_id or self.user_id
        if not uid:
            raise ValueError("user_id is required for user-scoped dashboard statistics")
        return uuid.UUID(str(uid)) if not isinstance(uid, uuid.UUID) else uid

    def get_stats(self, user_id: uuid.UUID | None = None) -> DashboardStats:
        """Compute every dashboard metric for the user with two total queries."""
        uid = self._resolve_user_id(user_id)
        start = time.perf_counter()
        aggregates = self.db.execute(
            select(
                func.count(Job.id).label("total_jobs"),
                func.count(UserJob.match_score).label("scored_jobs"),
                func.avg(UserJob.match_score).label("average_match_score"),
                func.max(UserJob.match_score).label("best_match_score"),
                func.count(case((UserJob.status == "applied", 1))).label(
                    "applications_submitted"
                ),
                func.count(case((UserJob.match_score >= EXCELLENT_MIN, 1))).label(
                    "excellent"
                ),
                func.count(
                    case((UserJob.match_score.between(GOOD_MIN, EXCELLENT_MIN - 1), 1))
                ).label("good"),
                func.count(
                    case((UserJob.match_score.between(POSSIBLE_MIN, GOOD_MIN - 1), 1))
                ).label("possible"),
                func.count(case((UserJob.match_score < POSSIBLE_MIN, 1))).label("weak"),
            )
            .select_from(Job)
            .outerjoin(
                UserJob,
                and_(UserJob.job_id == Job.id, UserJob.user_id == uid),
            )
            .where(Job.expired_at.is_(None))
        ).one()

        top_matches = self._get_top_matches(uid)
        average = (
            round(float(aggregates.average_match_score), 1)
            if aggregates.average_match_score is not None
            else None
        )

        return DashboardStats(
            total_jobs=aggregates.total_jobs or 0,
            scored_jobs=aggregates.scored_jobs or 0,
            average_match_score=average,
            best_match_score=aggregates.best_match_score,
            applications_submitted=aggregates.applications_submitted or 0,
            quality_breakdown=MatchQualityBreakdown(
                excellent=aggregates.excellent or 0,
                good=aggregates.good or 0,
                possible=aggregates.possible or 0,
                weak=aggregates.weak or 0,
            ),
            top_matches=top_matches,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    def _get_top_matches(self, user_id: uuid.UUID) -> list[TopMatchItem]:
        """
        Top 5 scored jobs for this user, sorted descending by match_score.
        Unscored jobs (match_score IS NULL) are excluded.
        """
        rows = self.db.execute(
            select(
                Job.id,
                Job.title,
                Job.company,
                UserJob.match_score,
                Job.source,
                func.coalesce(UserJob.status, "saved").label("status"),
            )
            .join(UserJob, and_(UserJob.job_id == Job.id, UserJob.user_id == user_id))
            .where(UserJob.match_score.isnot(None), Job.expired_at.is_(None))
            .order_by(UserJob.match_score.desc())
            .limit(TOP_MATCHES_LIMIT)
        ).all()

        return [
            TopMatchItem(
                id=row.id,
                title=row.title,
                company=row.company,
                match_score=row.match_score,
                source=row.source,
                status=row.status,
                recommendation_label=recommendation_label(row.match_score),
            )
            for row in rows
        ]
