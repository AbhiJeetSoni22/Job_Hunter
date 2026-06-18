"""
Alembic migration environment.

Configured for:
  - Online migrations (direct DB connection)
  - SQLAlchemy 2.x
  - Auto-detecting models from app.database.Base

To generate a new migration:
    alembic revision --autogenerate -m "describe the change"

To apply migrations:
    alembic upgrade head
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Import Base so Alembic sees all model metadata ────────────────────────
# Add model imports here as they're created in Phase 1+:
#
#   from app.models import job, resume, scrape_run  # noqa: F401
#
# Models must be imported before autogenerate can detect them.
from app.database import Base  # noqa: F401
from app.config import get_settings

# ── Alembic config object ─────────────────────────────────────────────────
config = context.config

# Set up Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with the value from pydantic settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url_str)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without a live DB connection.
    Not used in normal workflow — included for completeness.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (default).

    Connects to the database and runs migrations directly.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,       # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()