from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TaskHistory
from app.db.session import get_engine
from app.main import create_app

MISSING_UUID = "00000000-0000-0000-0000-000000000999"


def _create_user(client: TestClient, *, username: str, email: str) -> str:
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
    owner_id = _create_user(
        client,
        username="maria",
        email="maria@example.com",
    )

    task_response = client.post(
        "/tasks",
        json={
            "title": "Поднять PostgreSQL",
            "description": "Добавить docker compose и миграции",
            "owner_id": owner_id,
            "assignee_id": owner_id,
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
    assert body["items"][0]["owner"] == {
        "id": owner_id,
        "username": "maria",
        "full_name": "Maria",
    }
    assert body["items"][0]["archived_at"] is None
    assert body["items"][0]["closed_at"] is None
    assert body["items"][0]["created_at"].endswith("+03:00")
    assert body["items"][0]["updated_at"].endswith("+03:00")


def test_task_contract_endpoints_work_together(
    migrated_sqlite_db: str,
) -> None:
    """проверяет ручки задач и связанные сущности"""

    client = TestClient(create_app())
    owner_id = _create_user(client, username="ivan", email="ivan@example.com")
    assignee_id = _create_user(
        client, username="anna", email="anna@example.com"
    )

    created_task = client.post(
        "/tasks",
        json={
            "title": "Подготовить api note",
            "description": "Согласовать контракт",
            "owner_id": owner_id,
            "status": "todo",
            "due_date": "2026-04-20T12:00:00",
        },
    )
    assert created_task.status_code == 201
    task_id = created_task.json()["id"]
    assert created_task.json()["history"][0]["action"] == "created"
    assert created_task.json()["due_date"] == "2026-04-20T12:00:00+03:00"

    fetched_task = client.get(f"/tasks/{task_id}")
    assert fetched_task.status_code == 200
    assert fetched_task.json()["title"] == "Подготовить api note"
    assert fetched_task.json()["owner"] == {
        "id": owner_id,
        "username": "ivan",
        "full_name": "Ivan",
    }
    assert fetched_task.json()["comments"] == []

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
    assert assign_response.json()["assignee"] == {
        "id": assignee_id,
        "username": "anna",
        "full_name": "Anna",
    }

    comment_response = client.post(
        f"/tasks/{task_id}/comments",
        json={
            "author_id": owner_id,
            "text": "Первый комментарий",
        },
    )
    assert comment_response.status_code == 201
    assert comment_response.json()["task_id"] == task_id
    assert comment_response.json()["author"] == {
        "id": owner_id,
        "username": "ivan",
        "full_name": "Ivan",
    }
    assert comment_response.json()["created_at"].endswith("+03:00")
    assert comment_response.json()["updated_at"].endswith("+03:00")

    comments_response = client.get(f"/tasks/{task_id}/comments")
    assert comments_response.status_code == 200
    assert comments_response.json() == [
        {
            "id": comment_response.json()["id"],
            "task_id": task_id,
            "author_id": owner_id,
            "text": "Первый комментарий",
            "created_at": comment_response.json()["created_at"],
            "updated_at": comment_response.json()["updated_at"],
            "author": {
                "id": owner_id,
                "username": "ivan",
                "full_name": "Ivan",
            },
        }
    ]

    detailed_task = client.get(f"/tasks/{task_id}")
    assert detailed_task.status_code == 200
    detailed_body = detailed_task.json()
    assert detailed_body["comment_count"] == 1
    assert len(detailed_body["comments"]) == 1
    assert detailed_body["comments"][0]["text"] == "Первый комментарий"
    assert [entry["action"] for entry in detailed_body["history"]] == [
        "created",
        "status_changed",
        "comment_added",
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
    assert "owner_username" in export_response.text

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
    owner_id = _create_user(client, username="olga", email="olga@example.com")
    assignee_id = _create_user(
        client, username="petr", email="petr@example.com"
    )

    created_task = client.post(
        "/tasks",
        json={
            "title": "Проверить историю",
            "description": "Нужны записи для создания, комментария и статуса",
            "owner_id": owner_id,
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

    with Session(get_engine()) as session:
        history_rows = session.scalars(
            select(TaskHistory)
            .where(TaskHistory.task_id == UUID(task_id))
            .order_by(TaskHistory.created_at.asc(), TaskHistory.id.asc())
        ).all()

    assert [
        {
            "action": row.action,
            "changed_by_user_id": str(row.changed_by_user_id),
            "old_status": row.old_status,
            "new_status": row.new_status,
            "comment_text": row.comment_text,
        }
        for row in history_rows
    ] == [
        {
            "action": "created",
            "changed_by_user_id": owner_id,
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
            "owner_id": first_user.json()["id"],
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

    response = client.get(f"/tasks/{MISSING_UUID}")

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "task_not_found",
        "message": f"Задача с id={MISSING_UUID} не найдена.",
        "details": {"task_id": MISSING_UUID},
    }


def test_update_task_returns_404_for_unknown_id(
    migrated_sqlite_db: str,
) -> None:
    """проверяет единый 404 для изменения отсутствующей задачи"""

    client = TestClient(create_app())

    response = client.patch(
        f"/tasks/{MISSING_UUID}",
        json={"title": "обновить несуществующую задачу"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "task_not_found",
        "message": f"Задача с id={MISSING_UUID} не найдена.",
        "details": {"task_id": MISSING_UUID},
    }


def test_assign_task_moves_todo_to_in_progress(
    migrated_sqlite_db: str,
) -> None:
    """проверяет контракт назначения исполнителя со сменой статуса"""

    client = TestClient(create_app())
    owner_id = _create_user(
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
            "owner_id": owner_id,
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


def test_close_task_changes_status_and_sets_closed_at(
    migrated_sqlite_db: str,
) -> None:
    """проверяет отдельную ручку закрытия задачи"""

    client = TestClient(create_app())
    owner_id = _create_user(client, username="nina", email="nina@example.com")

    create_response = client.post(
        "/tasks",
        json={
            "title": "Закрыть задачу",
            "description": "Проверить контракт close",
            "owner_id": owner_id,
            "status": "in_progress",
        },
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    close_response = client.post(
        f"/tasks/{task_id}/close",
        json={"changed_by_user_id": owner_id},
    )

    assert close_response.status_code == 200
    assert close_response.json()["status"] == "done"
    assert close_response.json()["closed_at"] is not None
    assert close_response.json()["closed_at"].endswith("+03:00")

    second_close = client.post(
        f"/tasks/{task_id}/close",
        json={"changed_by_user_id": owner_id},
    )

    assert second_close.status_code == 409
    assert second_close.json() == {
        "error_code": "task_already_closed",
        "message": "Задача уже закрыта.",
        "details": {"task_id": task_id, "status": "done"},
    }


def test_status_update_clears_closed_at_when_task_reopens(
    migrated_sqlite_db: str,
) -> None:
    """проверяет согласованность closed_at при смене статуса"""

    client = TestClient(create_app())
    owner_id = _create_user(client, username="max", email="max@example.com")

    task_response = client.post(
        "/tasks",
        json={
            "title": "Переоткрыть задачу",
            "owner_id": owner_id,
            "status": "in_progress",
        },
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    close_response = client.patch(
        f"/tasks/{task_id}/status",
        json={
            "status": "done",
            "changed_by_user_id": owner_id,
        },
    )
    assert close_response.status_code == 200
    assert close_response.json()["closed_at"] is not None

    reopen_response = client.patch(
        f"/tasks/{task_id}/status",
        json={
            "status": "in_progress",
            "changed_by_user_id": owner_id,
        },
    )
    assert reopen_response.status_code == 200
    assert reopen_response.json()["closed_at"] is None


def test_comment_update_uses_separate_update_schema(
    migrated_sqlite_db: str,
) -> None:
    """проверяет отдельную модель обновления комментария"""

    client = TestClient(create_app())
    owner_id = _create_user(client, username="kate", email="kate@example.com")

    task_response = client.post(
        "/tasks",
        json={
            "title": "Обновить комментарий",
            "owner_id": owner_id,
        },
    )
    assert task_response.status_code == 201

    comment_response = client.post(
        f"/tasks/{task_response.json()['id']}/comments",
        json={
            "author_id": owner_id,
            "text": "Исходный комментарий",
        },
    )
    assert comment_response.status_code == 201

    updated_comment = client.patch(
        f"/comments/{comment_response.json()['id']}",
        json={"text": "Обновленный комментарий"},
    )
    assert updated_comment.status_code == 200
    assert updated_comment.json()["text"] == "Обновленный комментарий"
    assert updated_comment.json()["author"] == {
        "id": owner_id,
        "username": "kate",
        "full_name": "Kate",
    }


def test_task_create_rejects_extra_fields(
    migrated_sqlite_db: str,
) -> None:
    """проверяет запрет лишних полей при создании задачи"""

    client = TestClient(create_app())
    owner_id = _create_user(
        client, username="extra", email="extra@example.com"
    )

    response = client.post(
        "/tasks",
        json={
            "title": "лишнее поле",
            "owner_id": owner_id,
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
    owner_id = _create_user(
        client, username="patcher", email="patcher@example.com"
    )
    task_id = client.post(
        "/tasks",
        json={
            "title": "обновляемая задача",
            "owner_id": owner_id,
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
    owner_id = _create_user(
        client, username="empty", email="empty@example.com"
    )
    task_id = client.post(
        "/tasks",
        json={
            "title": "пустой patch",
            "owner_id": owner_id,
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


def test_create_task_returns_404_when_owner_does_not_exist(
    migrated_sqlite_db: str,
) -> None:
    """проверяет что создание задачи с неизвестным owner_id дает 404"""

    client = TestClient(create_app())

    response = client.post(
        "/tasks",
        json={
            "title": "Новая задача",
            "description": "Без существующего owner",
            "owner_id": MISSING_UUID,
            "status": "todo",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "user_not_found",
        "message": (
            f"Пользователь для поля owner_id с id={MISSING_UUID} " "не найден."
        ),
        "details": {"field": "owner_id", "user_id": MISSING_UUID},
    }
