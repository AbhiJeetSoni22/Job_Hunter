"""
Shared FastAPI dependencies.

Import these in routers with Depends():

    from app.dependencies import get_db_session, get_active_resume

The db session dependency lives here (not in database.py) so routers
have a single import location for all dependency functions.
"""

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal


# ── Database session ───────────────────────────────────────────────────────
def get_db_session() -> Generator[Session, None, None]:
    """
    Yield a database session scoped to a single HTTP request.

    Automatically closed after the request completes, even on exception.

    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db_session)) -> ...:
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Convenience type alias ─────────────────────────────────────────────────
# Use this in router function signatures for cleaner type hints:
#
#   from typing import Annotated
#   from app.dependencies import DbSession
#
#   def my_route(db: DbSession) -> ...:
#
from typing import Annotated  # noqa: E402

DbSession = Annotated[Session, Depends(get_db_session)]


# ── Placeholder: active resume dependency ─────────────────────────────────
# Added in Phase 2. Documented here so routers know where to import from.
#
# def get_active_resume(db: DbSession) -> Resume:
#     """Return active resume or raise 422 NO_RESUME."""
#     from app.services.resume_service import ResumeService
#     resume = ResumeService(db).get_resume()
#     if resume is None:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail={"code": "NO_RESUME", "message": "Upload a resume before scoring jobs"},
#         )
#     return resume