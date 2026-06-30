"""
test_dashboard_service.py

Tests for app.services.dashboard_service.DashboardService (Phase 5).

Coverage:
  - get_stats() metrics: total_jobs, scored_jobs, average/best score,
    applications_submitted
  - Match quality breakdown bucket boundaries (90/75/60)
  - Top Matches: top 5 only, sorted desc, unscored jobs excluded
  - recommendation_label exposed on TopMatchItem

All tests require a live PostgreSQL database (JSONB + UUID).
Skip gracefully when TEST_DATABASE_URL is absent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from tests.conftest import needs_db

pytestmark = needs_db


def _make_job(db, *, score=None, status="saved", title="Job", company="Co", source="remoteok"):
    from app.models.job import Job  # noqa: PLC0415

    now = datetime.now(timezone.utc)
    job = Job(
        id=str(uuid.uuid4()),
        title=title,
        company=company,
        description="desc",
        url=f"https://dashboard-test.example.com/{uuid.uuid4()}",
        source=source,
        status=status,
        match_score=score,
        matched_at=now if score is not None else None,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture()
def dashboard_service(db):
    from app.services.dashboard_service import DashboardService  # noqa: PLC0415

    return DashboardService(db)


# ---------------------------------------------------------------------------
# Dashboard metrics (Feature 3)
# ---------------------------------------------------------------------------

class TestDashboardMetrics:

    def test_empty_db_returns_zeroed_stats(self, dashboard_service):
        stats = dashboard_service.get_stats()
        assert stats.total_jobs == 0
        assert stats.scored_jobs == 0
        assert stats.average_match_score is None
        assert stats.best_match_score is None
        assert stats.applications_submitted == 0
        assert stats.top_matches == []

    def test_total_and_scored_counts(self, db, dashboard_service):
        _make_job(db, score=90)
        _make_job(db, score=None)
        _make_job(db, score=70)

        stats = dashboard_service.get_stats()
        assert stats.total_jobs == 3
        assert stats.scored_jobs == 2

    def test_average_and_best_score(self, db, dashboard_service):
        _make_job(db, score=80)
        _make_job(db, score=60)

        stats = dashboard_service.get_stats()
        assert stats.average_match_score == 70.0
        assert stats.best_match_score == 80

    def test_applications_submitted_counts_applied_status(self, db, dashboard_service):
        _make_job(db, score=90, status="applied")
        _make_job(db, score=85, status="applied")
        _make_job(db, score=50, status="saved")

        stats = dashboard_service.get_stats()
        assert stats.applications_submitted == 2


# ---------------------------------------------------------------------------
# Match quality breakdown (Feature 2)
# ---------------------------------------------------------------------------

class TestMatchQualityBreakdown:

    def test_bucket_boundaries(self, db, dashboard_service):
        _make_job(db, score=90)  # excellent (boundary)
        _make_job(db, score=89)  # good (boundary)
        _make_job(db, score=75)  # good (boundary)
        _make_job(db, score=74)  # possible (boundary)
        _make_job(db, score=60)  # possible (boundary)
        _make_job(db, score=59)  # weak (boundary)
        _make_job(db, score=None)  # unscored — excluded entirely

        breakdown = dashboard_service.get_stats().quality_breakdown
        assert breakdown.excellent == 1
        assert breakdown.good == 2
        assert breakdown.possible == 2
        assert breakdown.weak == 1


# ---------------------------------------------------------------------------
# Top matches (Feature 1)
# ---------------------------------------------------------------------------

class TestTopMatches:

    def test_excludes_unscored_jobs(self, db, dashboard_service):
        _make_job(db, score=None)
        scored = _make_job(db, score=95)

        top = dashboard_service.get_stats().top_matches
        assert len(top) == 1
        assert top[0].id == scored.id

    def test_sorted_descending(self, db, dashboard_service):
        _make_job(db, score=50, title="Low")
        _make_job(db, score=95, title="High")
        _make_job(db, score=70, title="Mid")

        top = dashboard_service.get_stats().top_matches
        scores = [item.match_score for item in top]
        assert scores == sorted(scores, reverse=True)
        assert top[0].title == "High"

    def test_limited_to_top_5(self, db, dashboard_service):
        for i in range(8):
            _make_job(db, score=50 + i)

        top = dashboard_service.get_stats().top_matches
        assert len(top) == 5

    def test_top_match_fields(self, db, dashboard_service):
        _make_job(db, score=96, title="Frontend Engineer", company="Acme", source="remoteok")

        item = dashboard_service.get_stats().top_matches[0]
        assert item.title == "Frontend Engineer"
        assert item.company == "Acme"
        assert item.source == "remoteok"
        assert item.status == "saved"
        assert item.recommendation_label == "Excellent Match"
