from fastapi.testclient import TestClient

from app.main import create_app


def test_list_tasks_returns_in_memory_tasks() -> None:
    client = TestClient(create_app())
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "title": "Разобрать flow запроса", "done": True},
        {"id": 2, "title": "Вынести tasks в сервис", "done": False},
    ]
