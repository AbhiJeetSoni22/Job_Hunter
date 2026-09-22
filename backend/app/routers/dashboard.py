"""
routers/dashboard.py

HTTP layer for the AI-powered recommendation dashboard (Phase 5).

  GET /api/dashboard/stats — Top Matches, Match Quality Breakdown, and
  summary metric cards (Total Jobs, Scored Jobs, Average/Best Match
  Score, Applications Submitted).

Multi-user architecture:
  - Scoped to the authenticated user's UserJob records and resume.
"""

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession
from app.schemas.dashboard import DashboardStats
from app.schemas.job import ApiResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/stats",
    response_model=ApiResponse[DashboardStats],
    summary="Dashboard summary statistics",
    description=(
        "Aggregate metrics for the recommendation dashboard for the authenticated user: "
        "total jobs, scored jobs, average and best match score, applications "
        "submitted, a match-quality breakdown (Excellent/Good/Possible/"
        "Weak), and the top 5 scored jobs."
    ),
)
def dashboard_stats(
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[DashboardStats]:
    stats = DashboardService(db).get_stats(user_id=user.id)
    return ApiResponse(data=stats)
