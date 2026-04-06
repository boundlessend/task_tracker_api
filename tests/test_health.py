from fastapi.testclient import TestClient

from app.main import create_app


def test_healthcheck_returns_ok(migrated_sqlite_db: str) -> None:
    """проверяет health-эндпоинт"""

    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Task Tracker API"
    assert body["env"] == "test"
    assert body["debug"] is False
    assert body["database"]["ok"] is True
