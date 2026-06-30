"""
Pydantic schemas for dashboard summary statistics.

Phase 5 — AI-powered recommendation dashboard:
  - Feature 1: Top Matches  -> TopMatchItem
  - Feature 2: Match Quality Breakdown -> MatchQualityBreakdown
  - Feature 3: Dashboard Metrics -> DashboardStats

Returned by GET /api/dashboard/stats. Every field is computed with
aggregate SQL (COUNT / AVG / MAX with CASE WHEN) plus a single indexed
top-N query — there is no per-job iteration in Python and no N+1
query pattern (see services/dashboard_service.py).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Feature 1 — Top Matches
# ---------------------------------------------------------------------------


class TopMatchItem(BaseModel):
    """
    Compact representation of a top-scoring job for the dashboard.

    Mirrors the fields requested by the Top Matches spec: title,
    company, match score, source, and job status.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company: str
    match_score: int
    source: str
    status: str

    # Human-readable label derived from match_score (Feature 5)
    recommendation_label: str | None = None


# ---------------------------------------------------------------------------
# Feature 2 — Match Quality Breakdown
# ---------------------------------------------------------------------------


class MatchQualityBreakdown(BaseModel):
    """Counts of scored jobs bucketed by match-quality tier."""

    excellent: int = Field(..., description="match_score >= 90", ge=0)
    good: int = Field(..., description="75 <= match_score <= 89", ge=0)
    possible: int = Field(..., description="60 <= match_score <= 74", ge=0)
    weak: int = Field(..., description="match_score < 60", ge=0)


# ---------------------------------------------------------------------------
# Feature 3 — Dashboard Metrics
# ---------------------------------------------------------------------------


class DashboardStats(BaseModel):
    """Aggregate dashboard summary returned by GET /api/dashboard/stats."""

    total_jobs: int = Field(..., ge=0)
    scored_jobs: int = Field(..., ge=0)
    average_match_score: float | None = Field(
        default=None, description="Average match_score across scored jobs, rounded to 1dp."
    )
    best_match_score: int | None = None
    applications_submitted: int = Field(
        ..., ge=0, description="Count of jobs with status == 'applied'."
    )

    quality_breakdown: MatchQualityBreakdown
    top_matches: list[TopMatchItem]
