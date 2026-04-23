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


def test_login_returns_token_and_protected_endpoint_accepts_bearer(
    client: TestClient,
    create_user,
) -> None:
    """проверяет учебный логин и bearer-токен"""

    create_user(username="nina", email="nina@example.com")

    login_response = client.post(
        "/auth/login",
        json={"username": "nina"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["access_token"] == "stub:nina"

    task_response = client.post(
        "/tasks",
        json={"title": "Задача по токену"},
        headers={"Authorization": "Bearer stub:nina"},
    )

    assert task_response.status_code == 201
    assert task_response.json()["owner"]["username"] == "nina"


def test_protected_task_endpoint_requires_auth(
    client: TestClient,
    create_user,
    create_task,
) -> None:
    """проверяет что защищенная ручка без логина недоступна"""

    create_user(username="nina", email="nina@example.com")
    created_task = create_task(username="nina", title="Закрыть задачу")

    response = client.get(f"/tasks/{created_task['id']}")

    assert response.status_code == 401
    assert response.json()["error_code"] == "authentication_error"


def test_create_read_and_close_task_api_flow(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """покрывает создание чтение и закрытие задачи через api"""

    create_user(username="nina", email="nina@example.com")
    created_task = create_task(
        username="nina",
        title="Закрыть задачу",
        description="Проверить контракт close",
        status="in_progress",
    )
    task_id = created_task["id"]

    fetched_task = client.get(f"/tasks/{task_id}", headers=auth_headers("nina"))

    assert fetched_task.status_code == 200
    assert fetched_task.json()["title"] == "Закрыть задачу"
    assert fetched_task.json()["owner"]["username"] == "nina"
    assert fetched_task.json()["comments"] == []

    close_response = client.post(
        f"/tasks/{task_id}/close",
        headers=auth_headers("nina"),
    )

    assert close_response.status_code == 200
    assert close_response.json()["status"] == "done"
    assert close_response.json()["closed_at"] is not None
    assert close_response.json()["closed_at"].endswith("+03:00")


def test_owner_admin_rule_blocks_stranger_and_allows_admin(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """проверяет правило owner/admin для чтения чужой задачи"""

    create_user(username="owner", email="owner@example.com")
    create_user(username="stranger", email="stranger@example.com")
    create_user(
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    created_task = create_task(username="owner", title="Чужая задача")

    stranger_response = client.get(
        f"/tasks/{created_task['id']}",
        headers=auth_headers("stranger"),
    )
    admin_response = client.get(
        f"/tasks/{created_task['id']}",
        headers=auth_headers("admin"),
    )

    assert stranger_response.status_code == 403
    assert stranger_response.json()["error_code"] == "forbidden"
    assert admin_response.status_code == 200
    assert admin_response.json()["id"] == created_task["id"]


def test_task_detail_includes_assignment_comment_and_history(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """проверяет детальный контракт задачи со связанными сущностями"""

    create_user(username="ivan", email="ivan@example.com")
    anna_id = create_user(username="anna", email="anna@example.com")
    created_task = create_task(
        username="ivan",
        title="Подготовить api note",
        description="Согласовать контракт",
        due_date="2026-04-20T12:00:00",
    )
    task_id = created_task["id"]

    assign_response = client.post(
        f"/tasks/{task_id}/assign",
        json={"assignee_id": anna_id},
        headers=auth_headers("ivan"),
    )
    comment_response = client.post(
        f"/tasks/{task_id}/comments",
        json={"text": "Первый комментарий"},
        headers=auth_headers("ivan"),
    )
    detailed_task = client.get(f"/tasks/{task_id}", headers=auth_headers("ivan"))

    assert assign_response.status_code == 403
    assert assign_response.json()["error_code"] == "forbidden"

    assert comment_response.status_code == 201
    assert comment_response.json()["task_id"] == task_id
    assert comment_response.json()["author"]["username"] == "ivan"

    assert detailed_task.status_code == 200
    body = detailed_task.json()
    assert body["due_date"] == "2026-04-20T12:00:00+03:00"
    assert body["comment_count"] == 1
    assert len(body["comments"]) == 1
    assert body["comments"][0]["text"] == "Первый комментарий"
    assert [entry["action"] for entry in body["history"]] == [
        "created",
        "comment_added",
    ]


def test_assign_task_respects_role_rules(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """проверяет ограничения на назначение исполнителя"""

    owner_id = create_user(username="owner", email="owner@example.com")
    worker_id = create_user(username="worker", email="worker@example.com")
    create_user(
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    created_task = create_task(username="owner", title="Назначить исполнителя")

    owner_assign_self = client.post(
        f"/tasks/{created_task['id']}/assign",
        json={"assignee_id": owner_id},
        headers=auth_headers("owner"),
    )
    admin_assign_worker = client.post(
        f"/tasks/{created_task['id']}/assign",
        json={"assignee_id": worker_id},
        headers=auth_headers("admin"),
    )

    assert owner_assign_self.status_code == 200
    assert owner_assign_self.json()["assignee"]["username"] == "owner"
    assert owner_assign_self.json()["status"] == "in_progress"

    assert admin_assign_worker.status_code == 200
    assert admin_assign_worker.json()["assignee"]["username"] == "worker"


def test_list_tasks_supports_filters_sorting_and_pagination(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """проверяет список задач с фильтрами сортировкой и пагинацией"""

    owner_id = create_user(username="maria", email="maria@example.com")

    first_task = create_task(username="maria", title="Первая задача")
    time.sleep(0.01)
    second_task = create_task(username="maria", title="Вторая задача")
    create_task(username="maria", title="Третья задача", status="done")

    first_assign = client.post(
        f"/tasks/{first_task['id']}/assign",
        json={"assignee_id": owner_id},
        headers=auth_headers("maria"),
    )
    time.sleep(0.01)
    second_assign = client.post(
        f"/tasks/{second_task['id']}/assign",
        json={"assignee_id": owner_id},
        headers=auth_headers("maria"),
    )

    first_page = client.get(
        "/tasks",
        params={
            "status": "in_progress",
            "assignee_id": owner_id,
            "sort_by": "updated_at",
            "sort_order": "desc",
            "limit": 1,
            "offset": 0,
        },
        headers=auth_headers("maria"),
    )
    second_page = client.get(
        "/tasks",
        params={
            "status": "in_progress",
            "assignee_id": owner_id,
            "sort_by": "updated_at",
            "sort_order": "desc",
            "limit": 1,
            "offset": 1,
        },
        headers=auth_headers("maria"),
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
    assert first_page.json()["items"][0]["assignee_id"] == owner_id
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
    auth_headers,
) -> None:
    """проверяет агрегированную сводку по задачам"""

    create_user(username="olga", email="olga@example.com")
    todo_task = create_task(username="olga", title="todo")
    in_progress_task = create_task(
        username="olga",
        title="in_progress",
        status="in_progress",
    )
    create_task(username="olga", title="done", status="done")

    archive_response = client.post(
        f"/tasks/{in_progress_task['id']}/archive",
        headers=auth_headers("olga"),
    )
    summary_response = client.get("/tasks/summary", headers=auth_headers("olga"))

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
    auth_headers,
) -> None:
    """проверяет csv-контракт экспорта задач"""

    owner_id = create_user(username="sergey", email="sergey@example.com")
    created_task = create_task(
        username="sergey",
        assignee_id=owner_id,
        title="Подготовить выгрузку",
        description="Проверить csv контракт",
        due_date="2026-04-20T12:00:00",
    )
    task_id = created_task["id"]
    comment_response = client.post(
        f"/tasks/{task_id}/comments",
        json={"text": "Комментарий для выгрузки"},
        headers=auth_headers("sergey"),
    )

    export_response = client.get(
        "/tasks/export",
        params={"owner_id": owner_id, "sort_by": "updated_at"},
        headers=auth_headers("sergey"),
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
    assert rows[0]["id"] == task_id
    assert rows[0]["owner_id"] == owner_id
    assert rows[0]["owner_username"] == "sergey"
    assert rows[0]["assignee_id"] == owner_id
    assert rows[0]["comment_count"] == "1"


def test_create_task_validation_error_has_no_side_effect(
    client: TestClient,
    create_user,
    db_session: Session,
    auth_headers,
) -> None:
    """проверяет что ошибка валидации не создает задачу"""

    create_user(username="extra", email="extra@example.com")

    response = client.post(
        "/tasks",
        json={
            "title": "лишнее поле",
            "unexpected": True,
        },
        headers=auth_headers("extra"),
    )

    db_session.expire_all()
    tasks_total = db_session.scalar(select(func.count()).select_from(Task))

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert response.json()["details"][0]["location"] == ["body", "unexpected"]
    assert tasks_total == 0


def test_get_task_returns_404_for_unknown_id(
    client: TestClient,
    create_user,
    auth_headers,
) -> None:
    """проверяет отдельный сценарий 404 для чтения одной задачи"""

    create_user(username="reader", email="reader@example.com")

    response = client.get(f"/tasks/{MISSING_UUID}", headers=auth_headers("reader"))

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
    auth_headers,
) -> None:
    """проверяет что 404 на patch не меняет существующие задачи"""

    create_user(username="patcher", email="patcher@example.com")
    created_task = create_task(
        username="patcher",
        title="обновляемая задача",
        description="должна остаться без изменений",
    )

    response = client.patch(
        f"/tasks/{MISSING_UUID}",
        json={"title": "обновить несуществующую задачу"},
        headers=auth_headers("patcher"),
    )

    db_session.expire_all()
    saved_task = db_session.get(Task, UUID(created_task["id"]))
    tasks_total = db_session.scalar(select(func.count()).select_from(Task))

    assert response.status_code == 404
    assert saved_task is not None
    assert saved_task.title == "обновляемая задача"
    assert tasks_total == 1


def test_close_task_conflict_has_no_additional_side_effect(
    client: TestClient,
    create_user,
    create_task,
    db_session: Session,
    auth_headers,
) -> None:
    """проверяет что повторное закрытие не создает побочных эффектов"""

    create_user(username="max", email="max@example.com")
    created_task = create_task(
        username="max",
        title="Закрыть один раз",
        status="in_progress",
    )
    task_id = created_task["id"]

    first_close = client.post(
        f"/tasks/{task_id}/close",
        headers=auth_headers("max"),
    )
    second_close = client.post(
        f"/tasks/{task_id}/close",
        headers=auth_headers("max"),
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
    auth_headers,
) -> None:
    """проверяет что непереданные поля patch остаются без изменений"""

    create_user(username="mila", email="mila@example.com")
    created_task = create_task(
        username="mila",
        title="Исходный заголовок",
        description="Исходное описание",
        due_date="2026-04-20T12:00:00",
    )

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"title": "Новый заголовок"},
        headers=auth_headers("mila"),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Новый заголовок"
    assert response.json()["description"] == "Исходное описание"
    assert response.json()["due_date"] == "2026-04-20T12:00:00+03:00"


def test_patch_allows_null_for_nullable_fields(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """проверяет что nullable поля можно очистить через patch"""

    create_user(username="kate", email="kate@example.com")
    created_task = create_task(
        username="kate",
        title="Очистить поля",
        description="Есть описание",
        due_date="2026-04-20T12:00:00",
    )

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"description": None, "due_date": None},
        headers=auth_headers("kate"),
    )

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["due_date"] is None


def test_patch_rejects_forbidden_fields_without_side_effect(
    client: TestClient,
    create_user,
    create_task,
    db_session: Session,
    auth_headers,
) -> None:
    """проверяет что patch не дает менять запрещенные поля"""

    create_user(username="roman", email="roman@example.com")
    created_task = create_task(username="roman", title="Статус меняется не тут")

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"status": "done"},
        headers=auth_headers("roman"),
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
    auth_headers,
) -> None:
    """проверяет что повторная установка того же статуса не пишет историю"""

    create_user(username="nina", email="nina@example.com")
    created_task = create_task(
        username="nina",
        title="Проверить повтор статуса",
        description="История не должна дублироваться",
    )
    task_id = created_task["id"]

    repeated_status = client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "todo"},
        headers=auth_headers("nina"),
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
    auth_headers,
) -> None:
    """проверяет согласованность closed_at при смене статуса"""

    create_user(username="andrey", email="andrey@example.com")
    created_task = create_task(
        username="andrey",
        title="Переоткрыть задачу",
        status="in_progress",
    )
    task_id = created_task["id"]

    close_response = client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "done"},
        headers=auth_headers("andrey"),
    )
    reopen_response = client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "in_progress"},
        headers=auth_headers("andrey"),
    )

    assert close_response.status_code == 200
    assert close_response.json()["closed_at"] is not None
    assert reopen_response.status_code == 200
    assert reopen_response.json()["closed_at"] is None


def test_comment_update_uses_separate_update_schema(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """проверяет отдельную модель обновления комментария"""

    create_user(username="lena", email="lena@example.com")
    created_task = create_task(username="lena", title="Обновить комментарий")

    comment_response = client.post(
        f"/tasks/{created_task['id']}/comments",
        json={"text": "Исходный комментарий"},
        headers=auth_headers("lena"),
    )
    updated_comment = client.patch(
        f"/comments/{comment_response.json()['id']}",
        json={"text": "Обновленный комментарий"},
        headers=auth_headers("lena"),
    )

    assert comment_response.status_code == 201
    assert updated_comment.status_code == 200
    assert updated_comment.json()["text"] == "Обновленный комментарий"
    assert updated_comment.json()["author"]["username"] == "lena"


def test_task_update_rejects_extra_fields(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """проверяет запрет лишних полей при обновлении задачи"""

    create_user(username="sveta", email="sveta@example.com")
    created_task = create_task(username="sveta", title="проверка patch")

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"unexpected": "value"},
        headers=auth_headers("sveta"),
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert response.json()["details"][0]["location"] == ["body", "unexpected"]


def test_task_update_requires_at_least_one_field(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """проверяет transport validation для пустого patch"""

    create_user(username="empty", email="empty@example.com")
    created_task = create_task(username="empty", title="пустой patch")

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={},
        headers=auth_headers("empty"),
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert response.json()["details"][0]["location"] == ["body"]


def test_list_tasks_validates_limit_and_offset(
    client: TestClient,
    create_user,
    auth_headers,
) -> None:
    """проверяет границы параметров пагинации"""

    create_user(username="pager", email="pager@example.com")

    response = client.get(
        "/tasks",
        params={"limit": 0, "offset": -1},
        headers=auth_headers("pager"),
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert {
        tuple(detail["location"]) for detail in response.json()["details"]
    } == {
        ("query", "limit"),
        ("query", "offset"),
    }


def test_create_task_handles_malformed_json(
    client: TestClient,
    create_user,
    auth_headers,
) -> None:
    """проверяет единый ответ на некорректный json"""

    create_user(username="broken", email="broken@example.com")

    response = client.post(
        "/tasks",
        content='{"title": "broken",',
        headers={
            "Content-Type": "application/json",
            **auth_headers("broken"),
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "malformed_json"
    assert response.json()["details"][0]["location"][0] == "body"


def test_deactivated_user_cannot_login_or_use_protected_routes(
    client: TestClient,
    create_user,
    create_task,
    auth_headers,
) -> None:
    """проверяет сценарий деактивации пользователя"""

    create_user(
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    target_id = create_user(username="deactivated", email="dead@example.com")
    task = create_task(username="deactivated", title="Скрытая задача")

    deactivate_response = client.post(
        f"/users/{target_id}/deactivate",
        headers=auth_headers("admin"),
    )
    login_response = client.post(
        "/auth/login",
        json={"username": "deactivated"},
    )
    task_response = client.get(
        f"/tasks/{task['id']}",
        headers=auth_headers("deactivated"),
    )

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert login_response.status_code == 403
    assert login_response.json()["error_code"] == "inactive_user"
    assert task_response.status_code == 403
    assert task_response.json()["error_code"] == "inactive_user"


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
            "assignee_id": first_user.json()["id"],
            "status": "todo",
        },
        headers={"X-Auth-User": "postgres_user"},
    )
    comment_response = client.post(
        f"/tasks/{task_response.json()['id']}/comments",
        json={"text": "Комментарий в PostgreSQL"},
        headers={"X-Auth-User": "postgres_user"},
    )
    tasks_response = client.get(
        "/tasks",
        params={
            "status": "todo",
            "sort_by": "updated_at",
            "sort_order": "desc",
        },
        headers={"X-Auth-User": "postgres_user"},
    )

    assert first_user.status_code == 201
    assert duplicate_email.status_code == 400
    assert duplicate_email.json()["error_code"] == "data_integrity_error"
    assert task_response.status_code == 201
    assert comment_response.status_code == 201
    assert tasks_response.status_code == 200
    assert tasks_response.json()["meta"]["count"] == 1
    assert tasks_response.json()["items"][0]["comment_count"] == 1
