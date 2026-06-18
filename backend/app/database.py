"""
Database setup for SQLAlchemy 2.x.

Three exports used throughout the application:
  - engine        : SQLAlchemy engine (used by Alembic and tests)
  - SessionLocal  : Session factory (used by get_db)
  - get_db        : FastAPI dependency that yields a request-scoped session
  - Base          : Declarative base all ORM models inherit from
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# ── Engine ─────────────────────────────────────────────────────────────────
# pool_pre_ping=True  — test connection before use; handles DB restarts.
# pool_size=5         — sufficient for single-user personal tool.
# max_overflow=10     — allows burst above pool_size.
engine = create_engine(
    settings.database_url_str,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.is_development,  # Log SQL in development only
)

# ── Session factory ────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Avoid lazy-load errors after commit
)


# ── Declarative base ───────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Base class for all ORM models.

    Import this in every model file:
        from app.database import Base
    """

    pass


# ── FastAPI dependency ─────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session for the duration of a single request.

    Usage in a router:
        @router.get("/example")
        def example(db: Session = Depends(get_db)) -> ...:
            ...

    The session is closed automatically after the request completes,
    even if an exception is raised.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Return True if the database is reachable, False otherwise.

    Used by the health endpoint to report database status.
    Runs a minimal query — no table access, no ORM overhead.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False