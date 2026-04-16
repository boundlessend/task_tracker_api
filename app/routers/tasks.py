from __future__ import annotations

import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.dependencies.services import CommentServiceDep, TaskServiceDep
from app.schemas.comments import CommentCreate, CommentRead, TaskCommentCreate
from app.schemas.tasks import (
    SortOrder,
    TaskAssign,
    TaskClose,
    TaskCreate,
    TaskListItemRead,
    TaskListResponse,
    TaskRead,
    TaskSortField,
    TaskStatus,
    TaskStatusUpdate,
    TaskSummaryByStatus,
    TaskSummaryRead,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _render_tasks_csv(tasks: list[TaskListItemRead]) -> str:
    """собирает csv с задачами"""

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
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
    )
    for task in tasks:
        writer.writerow(
            [
                str(task.id),
                task.title,
                task.description,
                task.status.value,
                str(task.owner_id),
                task.owner.username,
                task.owner.full_name,
                str(task.assignee_id) if task.assignee_id else None,
                task.assignee.username if task.assignee else None,
                task.assignee.full_name if task.assignee else None,
                task.due_date.isoformat() if task.due_date else None,
                task.archived_at.isoformat() if task.archived_at else None,
                task.closed_at.isoformat() if task.closed_at else None,
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
                task.comment_count,
            ]
        )
    return buffer.getvalue()


@router.get("", response_model=TaskListResponse)
def list_tasks(
    service: TaskServiceDep,
    status: TaskStatus | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    assignee_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: TaskSortField = Query(default=TaskSortField.UPDATED_AT),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
) -> TaskListResponse:
    """возвращает список задач с фильтрами и сортировкой"""

    return service.list_tasks(
        status=status,
        owner_id=owner_id,
        assignee_id=assignee_id,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/search", response_model=list[TaskListItemRead])
def search_tasks(
    service: TaskServiceDep,
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[TaskListItemRead]:
    """ищет задачи по тексту"""

    return service.search_tasks(query_text=q, limit=limit)


@router.get("/summary", response_model=TaskSummaryRead)
def get_summary(
    service: TaskServiceDep,
) -> TaskSummaryRead:
    """возвращает сводку по задачам"""

    return service.get_summary()


@router.get("/summary/statuses", response_model=list[TaskSummaryByStatus])
def get_summary_by_status(
    service: TaskServiceDep,
) -> list[TaskSummaryByStatus]:
    """возвращает сводку задач по статусам"""

    return service.get_summary_by_status()


@router.get("/export")
def export_tasks(
    service: TaskServiceDep,
    status: TaskStatus | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    assignee_id: UUID | None = Query(default=None),
    sort_by: TaskSortField = Query(default=TaskSortField.UPDATED_AT),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
) -> Response:
    """выгружает список задач в csv"""

    tasks = service.export_tasks(
        status=status,
        owner_id=owner_id,
        assignee_id=assignee_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return Response(
        content=_render_tasks_csv(tasks),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="tasks.csv"'},
    )


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: UUID,
    service: TaskServiceDep,
) -> TaskRead:
    """возвращает задачу по идентификатору"""

    return service.get_task(task_id)


@router.get("/{task_id}/comments", response_model=list[CommentRead])
def list_task_comments(
    task_id: UUID,
    task_service: TaskServiceDep,
    comment_service: CommentServiceDep,
) -> list[CommentRead]:
    """возвращает комментарии задачи"""

    task_service.get_task(task_id)
    return comment_service.list_comments(task_id=task_id)


@router.post("", response_model=TaskRead, status_code=201)
def create_task(
    payload: TaskCreate,
    service: TaskServiceDep,
) -> TaskRead:
    """создает задачу"""

    return service.create_task(payload)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    service: TaskServiceDep,
) -> TaskRead:
    """частично обновляет задачу"""

    return service.update_task(task_id=task_id, payload=payload)


@router.post("/{task_id}/assign", response_model=TaskRead)
def assign_task(
    task_id: UUID,
    payload: TaskAssign,
    service: TaskServiceDep,
) -> TaskRead:
    """назначает исполнителя задаче"""

    return service.assign_task(
        task_id=task_id,
        assignee_id=payload.assignee_id,
    )


@router.post("/{task_id}/close", response_model=TaskRead)
def close_task(
    task_id: UUID,
    payload: TaskClose,
    service: TaskServiceDep,
) -> TaskRead:
    """закрывает задачу"""

    return service.close_task(task_id=task_id, payload=payload)


@router.post(
    "/{task_id}/comments", response_model=CommentRead, status_code=201
)
def create_task_comment(
    task_id: UUID,
    payload: TaskCommentCreate,
    task_service: TaskServiceDep,
    comment_service: CommentServiceDep,
) -> CommentRead:
    """создает комментарий у задачи"""

    task_service.get_task(task_id)
    return comment_service.create_comment(
        CommentCreate(
            task_id=task_id,
            author_id=payload.author_id,
            text=payload.text,
        )
    )


@router.post("/{task_id}/archive", response_model=TaskRead)
def archive_task(
    task_id: UUID,
    service: TaskServiceDep,
) -> TaskRead:
    """архивирует задачу"""

    return service.archive_task(task_id)


@router.patch("/{task_id}/status", response_model=TaskRead)
def update_task_status(
    task_id: UUID,
    payload: TaskStatusUpdate,
    service: TaskServiceDep,
) -> TaskRead:
    """обновляет статус задачи"""

    return service.update_task_status(
        task_id=task_id,
        status=payload.status,
        changed_by_user_id=payload.changed_by_user_id,
    )
