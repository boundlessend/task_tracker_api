from sqlalchemy import text
from fastapi.testclient import TestClient

from app.db.session import get_engine
from app.main import create_app


def test_tasks_are_saved_in_database_between_requests(
    migrated_sqlite_db: str,
) -> None:
    """проверяет что задачи сохраняются в базе данных"""

    client = TestClient(create_app())

    author = client.post(
        "/users",
        json={
            "username": "maria",
            "email": "maria@example.com",
            "full_name": "Мария Смирнова",
        },
    )
    assert author.status_code == 201

    task_response = client.post(
        "/tasks",
        json={
            "title": "Поднять PostgreSQL",
            "description": "Добавить docker compose и миграции",
            "author_id": author.json()["id"],
            "assignee_id": author.json()["id"],
            "status": "todo",
        },
    )
    assert task_response.status_code == 201

    second_client = TestClient(create_app())
    tasks_response = second_client.get("/tasks")
    assert tasks_response.status_code == 200
    body = tasks_response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Поднять PostgreSQL"
    assert body[0]["status"] == "todo"
    assert body[0]["author_username"] == "maria"


def test_task_filters_search_summary_and_comments(
    migrated_sqlite_db: str,
) -> None:
    """проверяет sql-сценарии списка поиска сводки и комментариев"""

    client = TestClient(create_app())

    author_id = client.post(
        "/users",
        json={
            "username": "ivan",
            "email": "ivan@example.com",
            "full_name": "Иван Петров",
        },
    ).json()["id"]
    assignee_id = client.post(
        "/users",
        json={
            "username": "anna",
            "email": "anna@example.com",
            "full_name": "Анна Иванова",
        },
    ).json()["id"]

    first_task = client.post(
        "/tasks",
        json={
            "title": "Сделать первую миграцию",
            "description": "Создать users, tasks, comments",
            "author_id": author_id,
            "assignee_id": assignee_id,
            "status": "in_progress",
        },
    )
    second_task = client.post(
        "/tasks",
        json={
            "title": "Добавить индексы",
            "description": "Нужны индексы для списка задач",
            "author_id": author_id,
            "assignee_id": assignee_id,
            "status": "todo",
        },
    )
    assert first_task.status_code == 201
    assert second_task.status_code == 201

    comment = client.post(
        "/comments",
        json={
            "task_id": first_task.json()["id"],
            "author_id": author_id,
            "text": "Историю изменений тоже добавим",
        },
    )
    assert comment.status_code == 201

    filtered = client.get(
        "/tasks",
        params={
            "status": "in_progress",
            "assignee_id": assignee_id,
            "sort_by": "created_at",
            "sort_order": "asc",
        },
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["comment_count"] == 1

    search = client.get("/tasks/search", params={"q": "миграц"})
    assert search.status_code == 200
    assert len(search.json()) == 1
    assert search.json()[0]["title"] == "Сделать первую миграцию"

    summary = client.get("/tasks/summary/statuses")
    assert summary.status_code == 200
    assert summary.json() == [
        {"status": "in_progress", "task_count": 1},
        {"status": "todo", "task_count": 1},
    ]

    status_update = client.patch(
        f"/tasks/{second_task.json()['id']}/status",
        json={"status": "done", "changed_by_user_id": author_id},
    )
    assert status_update.status_code == 200
    assert status_update.json()["status"] == "done"

    comments = client.get(
        "/comments", params={"task_id": first_task.json()["id"]}
    )
    assert comments.status_code == 200
    assert comments.json()[0]["author_username"] == "ivan"


def test_task_history_is_written_for_create_status_and_comment(
    migrated_sqlite_db: str,
) -> None:
    """проверяет что история задачи пишется для ключевых действий"""

    client = TestClient(create_app())

    author_id = client.post(
        "/users",
        json={
            "username": "olga",
            "email": "olga@example.com",
            "full_name": "Ольга Соколова",
        },
    ).json()["id"]
    assignee_id = client.post(
        "/users",
        json={
            "username": "petr",
            "email": "petr@example.com",
            "full_name": "Пётр Орлов",
        },
    ).json()["id"]

    created_task = client.post(
        "/tasks",
        json={
            "title": "Проверить историю",
            "description": "Нужны записи для создания, комментария и статуса",
            "author_id": author_id,
            "assignee_id": assignee_id,
            "status": "todo",
        },
    )
    assert created_task.status_code == 201
    task_id = created_task.json()["id"]

    create_comment = client.post(
        "/comments",
        json={
            "task_id": task_id,
            "author_id": assignee_id,
            "text": "Комментарий для истории",
        },
    )
    assert create_comment.status_code == 201

    change_status = client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "in_progress", "changed_by_user_id": assignee_id},
    )
    assert change_status.status_code == 200

    with get_engine().connect() as connection:
        history_rows = (
            connection.execute(
                text(
                    """
                SELECT
                    action,
                    changed_by_user_id,
                    old_status,
                    new_status,
                    comment_text
                FROM task_history
                WHERE task_id = :task_id
                ORDER BY id ASC
                """
                ),
                {"task_id": task_id},
            )
            .mappings()
            .all()
        )

    assert history_rows == [
        {
            "action": "created",
            "changed_by_user_id": author_id,
            "old_status": None,
            "new_status": "todo",
            "comment_text": None,
        },
        {
            "action": "comment_added",
            "changed_by_user_id": assignee_id,
            "old_status": None,
            "new_status": None,
            "comment_text": "Комментарий для истории",
        },
        {
            "action": "status_changed",
            "changed_by_user_id": assignee_id,
            "old_status": "todo",
            "new_status": "in_progress",
            "comment_text": None,
        },
    ]
