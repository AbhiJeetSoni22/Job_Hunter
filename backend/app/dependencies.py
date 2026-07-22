"""
Shared FastAPI dependencies.

Import these in routers:

from app.dependencies import DbSession, get_active_resume

This module provides reusable dependency aliases and higher-level
dependencies built on top of app.database.get_db().
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

 
from app.database import get_db
from app.models.resume import Resume



# ── Convenience type alias ─────────────────────────────────────────────────
# Use this in router function signatures for cleaner type hints:
#
#   from typing import Annotated
#   from app.dependencies import DbSession
#
#   def my_route(db: DbSession) -> ...:
#
from typing import Annotated  # noqa: E402

DbSession = Annotated[Session, Depends(get_db)]


def get_active_resume(db: Session = Depends(get_db)) -> Resume:
    """
    FastAPI dependency — resolves to the most recently uploaded resume.
 
    Raises HTTP 422 NO_RESUME when no resume exists.
    Declared as Depends in any endpoint that requires a resume.
    """
    resume = (
        db.query(Resume)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "NO_RESUME",
                "message": "Upload a resume before scoring jobs",
            },
        )
    return resume