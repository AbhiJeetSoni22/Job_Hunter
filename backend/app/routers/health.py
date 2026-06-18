"""
Health router.

GET /api/health — liveness and database connectivity check.

Used to verify:
  - FastAPI is running
  - PostgreSQL is reachable
  - Docker Compose setup is correct

Returns 200 when healthy, 503 when database is unreachable.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.database import check_database_connection

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns application status and database connectivity.",
)
def health_check() -> JSONResponse:
    """
    Verify the application is running and the database is reachable.

    Responses:
      200 — application healthy, database connected
      503 — application running, database unreachable
    """
    db_connected = check_database_connection()

    if db_connected:
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "database": "connected"},
        )

    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "database": "unreachable"},
    )