"""
services/dashboard_service.py

Aggregate statistics for the AI-powered recommendation dashboard.

Phase 5:
  - Feature 1: Top Matches      -> top 5 scored jobs, sorted desc, excludes unscored
  - Feature 2: Match Quality    -> Excellent / Good / Possible / Weak counts
  - Feature 3: Dashboard Metrics -> Total Jobs, Scored Jobs, Average/Best score,
                                     Applications Submitted

Performance:
  All counts, the average, and the best score are computed with a single
  aggregate SQL query using CASE WHEN expressions — there is no per-row
  iteration in Python. Top Matches is one additional query that hits the
  existing idx_jobs_score index (ORDER BY match_score DESC LIMIT 5).
  Two total queries, regardless of how many jobs exist — no N+1.
"""

from __future__ import annotations

from sqlalchemy import case, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.job import Job
from app.schemas.dashboard import DashboardStats, MatchQualityBreakdown, TopMatchItem
from app.services.match_service import recommendation_label

TOP_MATCHES_LIMIT = 5

# Match-quality tier thresholds (Feature 2 — distinct from the
# recommendation-label thresholds used by Feature 5).
EXCELLENT_MIN = 90
GOOD_MIN = 75
POSSIBLE_MIN = 60


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_stats(self) -> DashboardStats:
        """Compute every dashboard metric with two total queries."""

        aggregates = self.db.execute(
            select(
                func.count(Job.id).label("total_jobs"),
                func.count(Job.match_score).label("scored_jobs"),
                func.avg(Job.match_score).label("average_match_score"),
                func.max(Job.match_score).label("best_match_score"),
                func.count(case((Job.status == "applied", 1))).label(
                    "applications_submitted"
                ),
                func.count(case((Job.match_score >= EXCELLENT_MIN, 1))).label(
                    "excellent"
                ),
                func.count(
                    case((Job.match_score.between(GOOD_MIN, EXCELLENT_MIN - 1), 1))
                ).label("good"),
                func.count(
                    case((Job.match_score.between(POSSIBLE_MIN, GOOD_MIN - 1), 1))
                ).label("possible"),
                func.count(case((Job.match_score < POSSIBLE_MIN, 1))).label("weak"),
            )
        ).one()

        top_matches = self._get_top_matches()

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

    def _get_top_matches(self) -> list[TopMatchItem]:
        """
        Top 5 scored jobs, sorted descending by match_score.
        Unscored jobs (match_score IS NULL) are excluded.
        """
        rows = self.db.scalars(
            select(Job)
            .where(Job.match_score.isnot(None))
            .order_by(Job.match_score.desc())
            .limit(TOP_MATCHES_LIMIT)
        ).all()

        return [
            TopMatchItem(
                id=job.id,
                title=job.title,
                company=job.company,
                match_score=job.match_score,
                source=job.source,
                status=job.status,
                recommendation_label=recommendation_label(job.match_score),
            )
            for job in rows
        ]
