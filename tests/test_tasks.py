from __future__ import annotations

import csv
import time
from io import StringIO
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Task, TaskHistory
from app.main import create_app

MISSING_UUID = "00000000-0000-0000-0000-000000000999"


def _parse_csv_rows(csv_text: str) -> tuple[list[str], list[dict[str, str]]]:
    """разбирает csv-ответ на заголовки и строки"""

    reader = csv.DictReader(StringIO(csv_text))
    return list(reader.fieldnames or []), list(reader)


def test_create_read_and_close_task_api_flow(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """покрывает создание чтение и закрытие задачи через api"""

    owner_id = create_user(username="nina", email="nina@example.com")
    created_task = create_task(
        owner_id=owner_id,
        title="Закрыть задачу",
        description="Проверить контракт close",
        status="in_progress",
    )
    task_id = created_task["id"]

    fetched_task = client.get(f"/tasks/{task_id}")

    assert fetched_task.status_code == 200
    assert fetched_task.json()["title"] == "Закрыть задачу"
    assert fetched_task.json()["owner"] == {
        "id": owner_id,
        "username": "nina",
        "full_name": "Nina",
    }
    assert fetched_task.json()["comments"] == []

    close_response = client.post(
        f"/tasks/{task_id}/close",
        json={"changed_by_user_id": owner_id},
    )

    assert close_response.status_code == 200
    assert close_response.json()["status"] == "done"
    assert close_response.json()["closed_at"] is not None
    assert close_response.json()["closed_at"].endswith("+03:00")


def test_task_detail_includes_assignment_comment_and_history(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет детальный контракт задачи со связанными сущностями"""

    owner_id = create_user(username="ivan", email="ivan@example.com")
    assignee_id = create_user(username="anna", email="anna@example.com")
    created_task = create_task(
        owner_id=owner_id,
        title="Подготовить api note",
        description="Согласовать контракт",
        due_date="2026-04-20T12:00:00",
    )
    task_id = created_task["id"]

    assign_response = client.post(
        f"/tasks/{task_id}/assign",
        json={"assignee_id": assignee_id},
    )
    comment_response = client.post(
        f"/tasks/{task_id}/comments",
        json={
            "author_id": owner_id,
            "text": "Первый комментарий",
        },
    )
    detailed_task = client.get(f"/tasks/{task_id}")

    assert assign_response.status_code == 200
    assert assign_response.json()["assignee"] == {
        "id": assignee_id,
        "username": "anna",
        "full_name": "Anna",
    }
    assert assign_response.json()["status"] == "in_progress"

    assert comment_response.status_code == 201
    assert comment_response.json()["task_id"] == task_id
    assert comment_response.json()["author"] == {
        "id": owner_id,
        "username": "ivan",
        "full_name": "Ivan",
    }

    assert detailed_task.status_code == 200
    body = detailed_task.json()
    assert body["due_date"] == "2026-04-20T12:00:00+03:00"
    assert body["comment_count"] == 1
    assert len(body["comments"]) == 1
    assert body["comments"][0]["text"] == "Первый комментарий"
    assert [entry["action"] for entry in body["history"]] == [
        "created",
        "status_changed",
        "comment_added",
    ]


def test_list_tasks_supports_filters_sorting_and_pagination(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет список задач с фильтрами сортировкой и пагинацией"""

    owner_id = create_user(username="maria", email="maria@example.com")
    assignee_id = create_user(username="oleg", email="oleg@example.com")

    first_task = create_task(owner_id=owner_id, title="Первая задача")
    time.sleep(0.01)
    second_task = create_task(owner_id=owner_id, title="Вторая задача")
    create_task(owner_id=owner_id, title="Третья задача", status="done")

    first_assign = client.post(
        f"/tasks/{first_task['id']}/assign",
        json={"assignee_id": assignee_id},
    )
    time.sleep(0.01)
    second_assign = client.post(
        f"/tasks/{second_task['id']}/assign",
        json={"assignee_id": assignee_id},
    )

    first_page = client.get(
        "/tasks",
        params={
            "status": "in_progress",
            "assignee_id": assignee_id,
            "sort_by": "updated_at",
            "sort_order": "desc",
            "limit": 1,
            "offset": 0,
        },
    )
    second_page = client.get(
        "/tasks",
        params={
            "status": "in_progress",
            "assignee_id": assignee_id,
            "sort_by": "updated_at",
            "sort_order": "desc",
            "limit": 1,
            "offset": 1,
        },
    )

    assert first_assign.status_code == 200
    assert second_assign.status_code == 200

    assert first_page.status_code == 200
    assert first_page.json()["meta"] == {
        "limit": 1,
        "offset": 0,
        "count": 1,
        "total": 2,
    }
    assert first_page.json()["items"][0]["id"] == second_task["id"]
    assert first_page.json()["items"][0]["assignee_id"] == assignee_id
    assert first_page.json()["items"][0]["status"] == "in_progress"

    assert second_page.status_code == 200
    assert second_page.json()["meta"] == {
        "limit": 1,
        "offset": 1,
        "count": 1,
        "total": 2,
    }
    assert second_page.json()["items"][0]["id"] == first_task["id"]


def test_tasks_summary_returns_aggregate_contract(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет агрегированную сводку по задачам"""

    owner_id = create_user(username="olga", email="olga@example.com")
    todo_task = create_task(owner_id=owner_id, title="todo")
    in_progress_task = create_task(
        owner_id=owner_id,
        title="in_progress",
        status="in_progress",
    )
    create_task(owner_id=owner_id, title="done", status="done")

    archive_response = client.post(f"/tasks/{in_progress_task['id']}/archive")
    summary_response = client.get("/tasks/summary")

    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None

    assert summary_response.status_code == 200
    assert summary_response.json() == {
        "total": 3,
        "archived": 1,
        "by_status": [
            {"status": "done", "task_count": 1},
            {"status": "in_progress", "task_count": 1},
            {"status": "todo", "task_count": 1},
        ],
    }
    assert todo_task["status"] == "todo"


def test_tasks_export_returns_csv_contract(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет csv-контракт экспорта задач"""

    owner_id = create_user(username="sergey", email="sergey@example.com")
    assignee_id = create_user(username="irina", email="irina@example.com")
    created_task = create_task(
        owner_id=owner_id,
        assignee_id=assignee_id,
        title="Подготовить выгрузку",
        description="Проверить csv контракт",
        due_date="2026-04-20T12:00:00",
    )
    task_id = created_task["id"]
    comment_response = client.post(
        f"/tasks/{task_id}/comments",
        json={"author_id": owner_id, "text": "Комментарий для выгрузки"},
    )

    export_response = client.get(
        "/tasks/export",
        params={"owner_id": owner_id, "sort_by": "updated_at"},
    )

    assert comment_response.status_code == 201
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert export_response.headers["content-disposition"] == (
        'attachment; filename="tasks.csv"'
    )

    headers, rows = _parse_csv_rows(export_response.text)

    assert headers == [
        "id",
        "title",
        "description",
        "status",
        "owner_id",
        "owner_username",
        "owner_full_name",
        "assignee_id",
        "assignee_username",
        "assignee_full_name",
        "due_date",
        "archived_at",
        "closed_at",
        "created_at",
        "updated_at",
        "comment_count",
    ]
    assert len(rows) == 1
    assert rows[0] == {
        "id": task_id,
        "title": "Подготовить выгрузку",
        "description": "Проверить csv контракт",
        "status": "todo",
        "owner_id": owner_id,
        "owner_username": "sergey",
        "owner_full_name": "Sergey",
        "assignee_id": assignee_id,
        "assignee_username": "irina",
        "assignee_full_name": "Irina",
        "due_date": "2026-04-20T12:00:00+03:00",
        "archived_at": "",
        "closed_at": "",
        "created_at": rows[0]["created_at"],
        "updated_at": rows[0]["updated_at"],
        "comment_count": "1",
    }
    assert rows[0]["created_at"].endswith("+03:00")
    assert rows[0]["updated_at"].endswith("+03:00")


def test_create_task_validation_error_has_no_side_effect(
    client: TestClient,
    create_user,
    db_session: Session,
) -> None:
    """проверяет что ошибка валидации не создает задачу"""

    owner_id = create_user(username="extra", email="extra@example.com")

    response = client.post(
        "/tasks",
        json={
            "title": "лишнее поле",
            "owner_id": owner_id,
            "unexpected": True,
        },
    )

    db_session.expire_all()
    tasks_total = db_session.scalar(select(func.count()).select_from(Task))

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert response.json()["details"][0]["location"] == ["body", "unexpected"]
    assert tasks_total == 0


def test_get_task_returns_404_for_unknown_id(client: TestClient) -> None:
    """проверяет отдельный сценарий 404 для чтения одной задачи"""

    response = client.get(f"/tasks/{MISSING_UUID}")

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "task_not_found",
        "message": f"Задача с id={MISSING_UUID} не найдена.",
        "details": {"task_id": MISSING_UUID},
    }


def test_update_unknown_task_has_no_side_effect(
    client: TestClient,
    create_user,
    create_task,
    db_session: Session,
) -> None:
    """проверяет что 404 на patch не меняет существующие задачи"""

    owner_id = create_user(username="patcher", email="patcher@example.com")
    created_task = create_task(
        owner_id=owner_id,
        title="обновляемая задача",
        description="должна остаться без изменений",
    )

    response = client.patch(
        f"/tasks/{MISSING_UUID}",
        json={"title": "обновить несуществующую задачу"},
    )

    db_session.expire_all()
    saved_task = db_session.get(Task, UUID(created_task["id"]))
    tasks_total = db_session.scalar(select(func.count()).select_from(Task))

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "task_not_found",
        "message": f"Задача с id={MISSING_UUID} не найдена.",
        "details": {"task_id": MISSING_UUID},
    }
    assert saved_task is not None
    assert saved_task.title == "обновляемая задача"
    assert tasks_total == 1


def test_close_task_conflict_has_no_additional_side_effect(
    client: TestClient,
    create_user,
    create_task,
    db_session: Session,
) -> None:
    """проверяет что повторное закрытие не создает побочных эффектов"""

    owner_id = create_user(username="max", email="max@example.com")
    created_task = create_task(
        owner_id=owner_id,
        title="Закрыть один раз",
        status="in_progress",
    )
    task_id = created_task["id"]

    first_close = client.post(
        f"/tasks/{task_id}/close",
        json={"changed_by_user_id": owner_id},
    )
    second_close = client.post(
        f"/tasks/{task_id}/close",
        json={"changed_by_user_id": owner_id},
    )

    db_session.expire_all()
    history_rows = db_session.scalars(
        select(TaskHistory)
        .where(TaskHistory.task_id == UUID(task_id))
        .order_by(TaskHistory.created_at.asc(), TaskHistory.id.asc())
    ).all()
    saved_task = db_session.get(Task, UUID(task_id))

    assert first_close.status_code == 200
    assert second_close.status_code == 409
    assert second_close.json() == {
        "error_code": "task_already_closed",
        "message": "Задача уже закрыта.",
        "details": {"task_id": task_id, "status": "done"},
    }
    assert saved_task is not None
    assert saved_task.status == "done"
    assert saved_task.closed_at is not None
    assert len(history_rows) == 2
    assert [row.action for row in history_rows] == [
        "created",
        "status_changed",
    ]


def test_patch_keeps_omitted_fields_unchanged(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет что непереданные поля patch остаются без изменений"""

    owner_id = create_user(username="mila", email="mila@example.com")
    created_task = create_task(
        owner_id=owner_id,
        title="Исходный заголовок",
        description="Исходное описание",
        due_date="2026-04-20T12:00:00",
    )

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"title": "Новый заголовок"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Новый заголовок"
    assert response.json()["description"] == "Исходное описание"
    assert response.json()["due_date"] == "2026-04-20T12:00:00+03:00"


def test_patch_allows_null_for_nullable_fields(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет что nullable поля можно очистить через patch"""

    owner_id = create_user(username="kate", email="kate@example.com")
    created_task = create_task(
        owner_id=owner_id,
        title="Очистить поля",
        description="Есть описание",
        due_date="2026-04-20T12:00:00",
    )

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"description": None, "due_date": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["due_date"] is None


def test_patch_rejects_forbidden_fields_without_side_effect(
    client: TestClient,
    create_user,
    create_task,
    db_session: Session,
) -> None:
    """проверяет что patch не дает менять запрещенные поля"""

    owner_id = create_user(username="roman", email="roman@example.com")
    created_task = create_task(
        owner_id=owner_id, title="Статус меняется не тут"
    )

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"status": "done"},
    )

    db_session.expire_all()
    saved_task = db_session.get(Task, UUID(created_task["id"]))

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert saved_task is not None
    assert saved_task.status == "todo"
    assert saved_task.closed_at is None


def test_update_task_status_does_not_duplicate_history_on_same_status(
    client: TestClient,
    create_user,
    create_task,
    db_session: Session,
) -> None:
    """проверяет что повторная установка того же статуса не пишет историю"""

    owner_id = create_user(username="nina", email="nina@example.com")
    created_task = create_task(
        owner_id=owner_id,
        title="Проверить повтор статуса",
        description="История не должна дублироваться",
    )
    task_id = created_task["id"]

    repeated_status = client.patch(
        f"/tasks/{task_id}/status",
        json={
            "status": "todo",
            "changed_by_user_id": owner_id,
        },
    )

    db_session.expire_all()
    history_rows = db_session.scalars(
        select(TaskHistory)
        .where(TaskHistory.task_id == UUID(task_id))
        .order_by(TaskHistory.created_at.asc(), TaskHistory.id.asc())
    ).all()

    assert repeated_status.status_code == 200
    assert [
        entry["action"] for entry in repeated_status.json()["history"]
    ] == ["created"]
    assert len(history_rows) == 1
    assert history_rows[0].action == "created"


def test_status_update_clears_closed_at_when_task_reopens(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет согласованность closed_at при смене статуса"""

    owner_id = create_user(username="andrey", email="andrey@example.com")
    created_task = create_task(
        owner_id=owner_id,
        title="Переоткрыть задачу",
        status="in_progress",
    )
    task_id = created_task["id"]

    close_response = client.patch(
        f"/tasks/{task_id}/status",
        json={
            "status": "done",
            "changed_by_user_id": owner_id,
        },
    )
    reopen_response = client.patch(
        f"/tasks/{task_id}/status",
        json={
            "status": "in_progress",
            "changed_by_user_id": owner_id,
        },
    )

    assert close_response.status_code == 200
    assert close_response.json()["closed_at"] is not None
    assert reopen_response.status_code == 200
    assert reopen_response.json()["closed_at"] is None


def test_comment_update_uses_separate_update_schema(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет отдельную модель обновления комментария"""

    owner_id = create_user(username="lena", email="lena@example.com")
    created_task = create_task(owner_id=owner_id, title="Обновить комментарий")

    comment_response = client.post(
        f"/tasks/{created_task['id']}/comments",
        json={
            "author_id": owner_id,
            "text": "Исходный комментарий",
        },
    )
    updated_comment = client.patch(
        f"/comments/{comment_response.json()['id']}",
        json={"text": "Обновленный комментарий"},
    )

    assert comment_response.status_code == 201
    assert updated_comment.status_code == 200
    assert updated_comment.json()["text"] == "Обновленный комментарий"
    assert updated_comment.json()["author"] == {
        "id": owner_id,
        "username": "lena",
        "full_name": "Lena",
    }


def test_task_update_rejects_extra_fields(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет запрет лишних полей при обновлении задачи"""

    owner_id = create_user(username="sveta", email="sveta@example.com")
    created_task = create_task(owner_id=owner_id, title="проверка patch")

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"unexpected": "value"},
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert response.json()["details"][0]["location"] == ["body", "unexpected"]


def test_task_update_requires_at_least_one_field(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет transport validation для пустого patch"""

    owner_id = create_user(username="empty", email="empty@example.com")
    created_task = create_task(owner_id=owner_id, title="пустой patch")

    response = client.patch(f"/tasks/{created_task['id']}", json={})

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert response.json()["details"][0]["location"] == ["body"]


def test_list_tasks_validates_limit_and_offset(client: TestClient) -> None:
    """проверяет границы параметров пагинации"""

    response = client.get("/tasks", params={"limit": 0, "offset": -1})

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert {
        tuple(detail["location"]) for detail in response.json()["details"]
    } == {
        ("query", "limit"),
        ("query", "offset"),
    }


def test_create_task_handles_malformed_json(client: TestClient) -> None:
    """проверяет единый ответ на некорректный json"""

    response = client.post(
        "/tasks",
        content='{"title": "broken",',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "malformed_json"
    assert response.json()["details"][0]["location"][0] == "body"


def test_create_task_returns_404_when_owner_does_not_exist(
    client: TestClient,
) -> None:
    """проверяет что создание задачи с неизвестным owner_id дает 404"""

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
            f"Пользователь для поля owner_id с id={MISSING_UUID} не найден."
        ),
        "details": {"field": "owner_id", "user_id": MISSING_UUID},
    }


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
    duplicate_email = client.post(
        "/users",
        json={
            "username": "postgres_user_2",
            "email": "POSTGRES@example.com",
            "full_name": "Postgres User Two",
        },
    )
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
    comment_response = client.post(
        f"/tasks/{task_response.json()['id']}/comments",
        json={
            "author_id": first_user.json()["id"],
            "text": "Комментарий в PostgreSQL",
        },
    )
    tasks_response = client.get(
        "/tasks",
        params={
            "status": "todo",
            "sort_by": "updated_at",
            "sort_order": "desc",
        },
    )

    assert first_user.status_code == 201
    assert duplicate_email.status_code == 400
    assert duplicate_email.json()["error_code"] == "data_integrity_error"
    assert task_response.status_code == 201
    assert comment_response.status_code == 201
    assert tasks_response.status_code == 200
    assert tasks_response.json()["meta"]["count"] == 1
    assert tasks_response.json()["items"][0]["comment_count"] == 1
