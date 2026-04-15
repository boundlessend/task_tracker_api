from sqlalchemy import text
from fastapi.testclient import TestClient

from app.db.session import get_engine
from app.main import create_app


def _create_user(client: TestClient, *, username: str, email: str) -> int:
    """создает пользователя и возвращает его id"""

    response = client.post(
        "/users",
        json={
            "username": username,
            "email": email,
            "full_name": username.title(),
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_tasks_are_saved_in_database_between_requests(
    migrated_sqlite_db: str,
) -> None:
    """проверяет что задачи сохраняются в базе данных"""

    client = TestClient(create_app())
    author_id = _create_user(
        client,
        username="maria",
        email="maria@example.com",
    )

    task_response = client.post(
        "/tasks",
        json={
            "title": "Поднять PostgreSQL",
            "description": "Добавить docker compose и миграции",
            "author_id": author_id,
            "assignee_id": author_id,
            "status": "todo",
        },
    )
    assert task_response.status_code == 201

    second_client = TestClient(create_app())
    tasks_response = second_client.get("/tasks")
    assert tasks_response.status_code == 200
    body = tasks_response.json()
    assert body["meta"] == {
        "limit": 50,
        "offset": 0,
        "count": 1,
        "total": 1,
    }
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Поднять PostgreSQL"
    assert body["items"][0]["status"] == "todo"
    assert body["items"][0]["author_username"] == "maria"
    assert body["items"][0]["archived_at"] is None


def test_task_contract_endpoints_work_together(
    migrated_sqlite_db: str,
) -> None:
    """проверяет новые ручки задач и форму ответов"""

    client = TestClient(create_app())
    author_id = _create_user(client, username="ivan", email="ivan@example.com")
    assignee_id = _create_user(
        client, username="anna", email="anna@example.com"
    )

    created_task = client.post(
        "/tasks",
        json={
            "title": "Подготовить api note",
            "description": "Согласовать контракт",
            "author_id": author_id,
            "status": "todo",
        },
    )
    assert created_task.status_code == 201
    task_id = created_task.json()["id"]

    fetched_task = client.get(f"/tasks/{task_id}")
    assert fetched_task.status_code == 200
    assert fetched_task.json()["title"] == "Подготовить api note"

    patched_task = client.patch(
        f"/tasks/{task_id}",
        json={
            "description": None,
            "due_date": None,
            "title": "Подготовить краткий api note",
        },
    )
    assert patched_task.status_code == 200
    assert patched_task.json()["title"] == "Подготовить краткий api note"
    assert patched_task.json()["description"] is None

    assign_response = client.post(
        f"/tasks/{task_id}/assign",
        json={"assignee_id": assignee_id},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["assignee_id"] == assignee_id
    assert assign_response.json()["assignee_username"] == "anna"

    comment_response = client.post(
        f"/tasks/{task_id}/comments",
        json={
            "author_id": author_id,
            "text": "Первый комментарий",
        },
    )
    assert comment_response.status_code == 201
    assert comment_response.json()["task_id"] == task_id

    comments_response = client.get(f"/tasks/{task_id}/comments")
    assert comments_response.status_code == 200
    assert comments_response.json() == [
        {
            "id": comment_response.json()["id"],
            "task_id": task_id,
            "author_id": author_id,
            "author_username": "ivan",
            "text": "Первый комментарий",
            "created_at": comment_response.json()["created_at"],
        }
    ]

    filtered_tasks = client.get(
        "/tasks",
        params={
            "status": "in_progress",
            "assignee_id": assignee_id,
            "sort_by": "created_at",
            "sort_order": "asc",
        },
    )
    assert filtered_tasks.status_code == 200
    filtered_body = filtered_tasks.json()
    assert filtered_body["meta"] == {
        "limit": 50,
        "offset": 0,
        "count": 1,
        "total": 1,
    }
    assert filtered_body["items"][0]["comment_count"] == 1

    summary_response = client.get("/tasks/summary")
    assert summary_response.status_code == 200
    assert summary_response.json() == {
        "total": 1,
        "archived": 0,
        "by_status": [{"status": "in_progress", "task_count": 1}],
    }

    export_response = client.get("/tasks/export")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "Подготовить краткий api note" in export_response.text
    assert "author_username" in export_response.text

    archive_response = client.post(f"/tasks/{task_id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None

    second_archive = client.post(f"/tasks/{task_id}/archive")
    assert second_archive.status_code == 409
    assert second_archive.json()["error_code"] == "task_conflict"

    forbidden_patch = client.patch(
        f"/tasks/{task_id}",
        json={"status": "done"},
    )
    assert forbidden_patch.status_code == 422
    assert forbidden_patch.json()["error_code"] == "validation_error"

    null_title_patch = client.patch(
        f"/tasks/{task_id}",
        json={"title": None},
    )
    assert null_title_patch.status_code == 422
    assert null_title_patch.json()["error_code"] == "validation_error"


def test_task_history_is_written_for_create_status_and_comment(
    migrated_sqlite_db: str,
) -> None:
    """проверяет что история задачи пишется для ключевых действий"""

    client = TestClient(create_app())
    author_id = _create_user(client, username="olga", email="olga@example.com")
    assignee_id = _create_user(
        client, username="petr", email="petr@example.com"
    )

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
        f"/tasks/{task_id}/comments",
        json={
            "author_id": assignee_id,
            "text": "Комментарий для истории",
        },
    )
    assert create_comment.status_code == 201

    change_status = client.patch(
        f"/tasks/{task_id}/status",
        json={
            "status": "in_progress",
            "changed_by_user_id": assignee_id,
        },
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


def test_postgres_flow_and_case_insensitive_email_unique(
    migrated_postgres_db: str,
) -> None:
    """проверяет postgres сценарий и ограничения схемы"""

    client = TestClient(create_app())

    first_user = client.post(
        "/users",
        json={
            "username": "postgres_user",
            "email": "postgres@example.com",
            "full_name": "Postgres User",
        },
    )
    assert first_user.status_code == 201

    duplicate_email = client.post(
        "/users",
        json={
            "username": "postgres_user_2",
            "email": "POSTGRES@example.com",
            "full_name": "Postgres User Two",
        },
    )
    assert duplicate_email.status_code == 400
    assert duplicate_email.json()["error_code"] == "data_integrity_error"

    task_response = client.post(
        "/tasks",
        json={
            "title": "Проверить PostgreSQL",
            "description": "Нужен прямой интеграционный тест",
            "author_id": first_user.json()["id"],
            "assignee_id": first_user.json()["id"],
            "status": "todo",
        },
    )
    assert task_response.status_code == 201

    comment_response = client.post(
        f"/tasks/{task_response.json()['id']}/comments",
        json={
            "author_id": first_user.json()["id"],
            "text": "Комментарий в PostgreSQL",
        },
    )
    assert comment_response.status_code == 201

    tasks_response = client.get(
        "/tasks",
        params={
            "status": "todo",
            "sort_by": "updated_at",
            "sort_order": "desc",
        },
    )
    assert tasks_response.status_code == 200
    body = tasks_response.json()
    assert body["meta"]["count"] == 1
    assert body["items"][0]["comment_count"] == 1


def test_get_task_returns_404_for_unknown_id(
    migrated_sqlite_db: str,
) -> None:
    """проверяет отдельный сценарий 404 для чтения одной задачи"""

    client = TestClient(create_app())

    response = client.get("/tasks/999999")

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "task_not_found",
        "message": "Задача с id=999999 не найдена.",
        "details": {"task_id": 999999},
    }


def test_update_task_returns_404_for_unknown_id(
    migrated_sqlite_db: str,
) -> None:
    """проверяет единый 404 для изменения отсутствующей задачи"""

    client = TestClient(create_app())

    response = client.patch(
        "/tasks/999999",
        json={"title": "обновить несуществующую задачу"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "task_not_found",
        "message": "Задача с id=999999 не найдена.",
        "details": {"task_id": 999999},
    }


def test_assign_task_moves_todo_to_in_progress(
    migrated_sqlite_db: str,
) -> None:
    """проверяет контракт назначения исполнителя со сменой статуса"""

    client = TestClient(create_app())
    author_id = _create_user(
        client, username="sergey", email="sergey@example.com"
    )
    assignee_id = _create_user(
        client, username="irina", email="irina@example.com"
    )

    create_response = client.post(
        "/tasks",
        json={
            "title": "Назначить исполнителя",
            "description": "После назначения задача должна стартовать",
            "author_id": author_id,
            "status": "todo",
        },
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    assign_response = client.post(
        f"/tasks/{task_id}/assign",
        json={"assignee_id": assignee_id},
    )

    assert assign_response.status_code == 200
    assert assign_response.json()["assignee_id"] == assignee_id
    assert assign_response.json()["status"] == "in_progress"


def test_close_task_changes_status_and_rejects_second_close(
    migrated_sqlite_db: str,
) -> None:
    """проверяет отдельную ручку закрытия задачи"""

    client = TestClient(create_app())
    author_id = _create_user(client, username="nina", email="nina@example.com")

    create_response = client.post(
        "/tasks",
        json={
            "title": "Закрыть задачу",
            "description": "Проверить контракт close",
            "author_id": author_id,
            "status": "in_progress",
        },
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    close_response = client.post(
        f"/tasks/{task_id}/close",
        json={"changed_by_user_id": author_id},
    )

    assert close_response.status_code == 200
    assert close_response.json()["status"] == "done"

    second_close = client.post(
        f"/tasks/{task_id}/close",
        json={"changed_by_user_id": author_id},
    )

    assert second_close.status_code == 409
    assert second_close.json() == {
        "error_code": "task_already_closed",
        "message": "Задача уже закрыта.",
        "details": {"task_id": task_id, "status": "done"},
    }


def test_task_create_rejects_extra_fields(
    migrated_sqlite_db: str,
) -> None:
    """проверяет запрет лишних полей при создании задачи"""

    client = TestClient(create_app())
    author_id = _create_user(
        client, username="extra", email="extra@example.com"
    )

    response = client.post(
        "/tasks",
        json={
            "title": "лишнее поле",
            "author_id": author_id,
            "unexpected": True,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["details"][0]["location"] == ["body", "unexpected"]


def test_task_update_rejects_extra_fields(
    migrated_sqlite_db: str,
) -> None:
    """проверяет запрет лишних полей при обновлении задачи"""

    client = TestClient(create_app())
    author_id = _create_user(
        client, username="patcher", email="patcher@example.com"
    )
    task_id = client.post(
        "/tasks",
        json={
            "title": "обновляемая задача",
            "author_id": author_id,
        },
    ).json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"unexpected": "value"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["details"][0]["location"] == ["body", "unexpected"]


def test_task_update_requires_at_least_one_field(
    migrated_sqlite_db: str,
) -> None:
    """проверяет transport validation для пустого patch"""

    client = TestClient(create_app())
    author_id = _create_user(
        client, username="empty", email="empty@example.com"
    )
    task_id = client.post(
        "/tasks",
        json={
            "title": "пустой patch",
            "author_id": author_id,
        },
    ).json()["id"]

    response = client.patch(f"/tasks/{task_id}", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["details"][0]["location"] == ["body"]


def test_list_tasks_validates_limit_and_offset(
    migrated_sqlite_db: str,
) -> None:
    """проверяет границы параметров пагинации"""

    client = TestClient(create_app())

    response = client.get("/tasks", params={"limit": 0, "offset": -1})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert {tuple(detail["location"]) for detail in body["details"]} == {
        ("query", "limit"),
        ("query", "offset"),
    }


def test_create_task_handles_malformed_json(
    migrated_sqlite_db: str,
) -> None:
    """проверяет единый ответ на некорректный json"""

    client = TestClient(create_app())

    response = client.post(
        "/tasks",
        data='{"title": "broken",',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "malformed_json"
    assert body["details"][0]["location"][0] == "body"
