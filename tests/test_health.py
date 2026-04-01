from fastapi.testclient import TestClient

from app.main import create_app


def test_healthcheck_returns_ok(migrated_sqlite_db: str) -> None:
    """проверяет health-эндпоинт"""

    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Task Tracker API",
        "env": "test",
        "debug": False,
    }
