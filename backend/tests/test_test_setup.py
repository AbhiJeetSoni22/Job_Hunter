"""
tests/test_test_setup.py — Verification tests for test infrastructure & safety guards.
"""

import pytest

from tests.conftest import validate_test_database_url


def test_validate_test_database_url_valid():
    """Valid PostgreSQL connection string with test database name passes."""
    validate_test_database_url("postgresql://user:pass@localhost:5432/test_db")
    validate_test_database_url("postgresql+psycopg2://user:pass@localhost:5432/my_test_db?sslmode=require")


def test_validate_test_database_url_rejects_empty():
    """Empty or unset URL string raises ValueError."""
    with pytest.raises(ValueError, match="empty or unset"):
        validate_test_database_url("")


def test_validate_test_database_url_rejects_sqlite():
    """SQLite connection strings are explicitly rejected."""
    with pytest.raises(ValueError, match="PostgreSQL connection string"):
        validate_test_database_url("sqlite:///:memory:")

    with pytest.raises(ValueError, match="PostgreSQL connection string"):
        validate_test_database_url("sqlite:///test_db.sqlite")


def test_validate_test_database_url_rejects_non_postgres():
    """Non-PostgreSQL connection strings (MySQL, Oracle) are rejected."""
    with pytest.raises(ValueError, match="PostgreSQL connection string"):
        validate_test_database_url("mysql://user:pass@localhost:3306/test_db")


def test_validate_test_database_url_rejects_non_test_db():
    """PostgreSQL DSN pointing to non-test database name (e.g. production/neondb) is rejected."""
    with pytest.raises(ValueError, match="Refusing to run tests against non-test database"):
        validate_test_database_url("postgresql://user:pass@localhost:5432/production_db")

    with pytest.raises(ValueError, match="Refusing to run tests against non-test database"):
        validate_test_database_url("postgresql://user:pass@localhost:5432/neondb")
