"""
routers/dashboard.py

HTTP layer for the AI-powered recommendation dashboard (Phase 5).

  GET /api/dashboard/stats — Top Matches, Match Quality Breakdown, and
  summary metric cards (Total Jobs, Scored Jobs, Average/Best Match
  Score, Applications Submitted).

Thin router — all logic lives in DashboardService.
"""

from app.dependencies import DbSession
from app.schemas.dashboard import DashboardStats
from app.schemas.job import ApiResponse
from app.services.dashboard_service import DashboardService
from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/stats",
    response_model=ApiResponse[DashboardStats],
    summary="Dashboard summary statistics",
    description=(
        "Aggregate metrics for the recommendation dashboard: total jobs, "
        "scored jobs, average and best match score, applications "
        "submitted, a match-quality breakdown (Excellent/Good/Possible/"
        "Weak), and the top 5 scored jobs. Computed with a single "
        "aggregate query plus one indexed top-N query — no N+1 queries."
    ),
)
def dashboard_stats(db: DbSession) -> ApiResponse[DashboardStats]:
    stats = DashboardService(db).get_stats()
    return ApiResponse(data=stats)
