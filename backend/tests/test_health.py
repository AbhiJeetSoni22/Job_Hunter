"""
tests/test_health.py — Tests for the lightweight liveness endpoint (GET /health).
"""

from fastapi.testclient import TestClient

from app.main import app


def test_liveness_check_returns_ok() -> None:
    """GET /health returns HTTP 200 and {'status': 'ok'} without database access."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
