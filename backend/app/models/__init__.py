"""
ORM model registry.

WHY THIS FILE EXISTS:
  Alembic's autogenerate (alembic revision --autogenerate) works by
  inspecting `Base.metadata`. SQLAlchemy only registers a model's table
  into Base.metadata when the model's module is imported. If a model
  file is never imported, its table is invisible to autogenerate — and
  the generated migration will silently drop it.

  Importing all models here and then importing this package from
  alembic/env.py guarantees every table is registered before Alembic
  reads metadata.

HOW TO ADD A NEW MODEL:
  1. Create app/models/your_model.py
  2. Add: from app.models.your_model import YourModel  (below)
  3. Add: __all__ entry
  4. Run: alembic revision --autogenerate -m "add your_model table"

IMPORT ORDER:
  Base must be imported before any model. Since all models import Base
  from app.database, and app.database has no model imports, there are
  no circular dependency risks.
"""

from app.models.job import Job
from app.models.resume import Resume
from app.models.scrape_run import ScrapeRun

__all__ = [
    "Job",
    "Resume",
    "ScrapeRun",
]