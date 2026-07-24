from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.app.main import app


def test_live() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_ready_when_dependencies_are_available() -> None:
    with patch(
        "backend.api.health.check_dependencies",
        new=AsyncMock(
            return_value={"postgres": "ok", "redis": "ok", "qdrant": "ok", "minio": "ok"}
        ),
    ):
        with TestClient(app) as client:
            response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_when_dependency_is_unavailable() -> None:
    with patch(
        "backend.api.health.check_dependencies",
        new=AsyncMock(
            return_value={"postgres": "ok", "redis": "unavailable", "qdrant": "ok", "minio": "ok"}
        ),
    ):
        with TestClient(app) as client:
            response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
