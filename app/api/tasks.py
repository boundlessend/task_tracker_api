from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.comments import get_comment_service
from app.db.session import get_db_session
from app.repositories.tasks import TaskRepository
from app.schemas.comments import CommentCreate, CommentRead, TaskCommentCreate
from app.schemas.tasks import (
    SortOrder,
    TaskAssign,
    TaskCreate,
    TaskListResponse,
    TaskRead,
    TaskSortField,
    TaskStatus,
    TaskStatusUpdate,
    TaskSummaryByStatus,
    TaskSummaryRead,
    TaskUpdate,
)
from app.services.comments import CommentService
from app.services.tasks import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(
    session: Session = Depends(get_db_session),
) -> TaskService:
    """создает сервис задач для запроса"""

    return TaskService(repository=TaskRepository(session=session))


def _render_tasks_csv(tasks: list[TaskRead]) -> str:
    """собирает csv с задачами"""

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "title",
            "description",
            "status",
            "author_id",
            "author_username",
            "assignee_id",
            "assignee_username",
            "due_date",
            "archived_at",
            "created_at",
            "updated_at",
            "comment_count",
        ]
    )
    for task in tasks:
        writer.writerow(
            [
                task.id,
                task.title,
                task.description,
                task.status.value,
                task.author_id,
                task.author_username,
                task.assignee_id,
                task.assignee_username,
                task.due_date.isoformat() if task.due_date else None,
                task.archived_at.isoformat() if task.archived_at else None,
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
                task.comment_count,
            ]
        )
    return buffer.getvalue()


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status: TaskStatus | None = Query(default=None),
    author_id: int | None = Query(default=None, gt=0),
    assignee_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: TaskSortField = Query(default=TaskSortField.UPDATED_AT),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
    service: TaskService = Depends(get_task_service),
) -> TaskListResponse:
    """возвращает список задач с фильтрами и сортировкой"""

    return service.list_tasks(
        status=status,
        author_id=author_id,
        assignee_id=assignee_id,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/search", response_model=list[TaskRead])
def search_tasks(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    service: TaskService = Depends(get_task_service),
) -> list[TaskRead]:
    """ищет задачи по тексту"""

    return service.search_tasks(query_text=q, limit=limit)


@router.get("/summary", response_model=TaskSummaryRead)
def get_summary(
    service: TaskService = Depends(get_task_service),
) -> TaskSummaryRead:
    """возвращает сводку по задачам"""

    return service.get_summary()


@router.get("/summary/statuses", response_model=list[TaskSummaryByStatus])
def get_summary_by_status(
    service: TaskService = Depends(get_task_service),
) -> list[TaskSummaryByStatus]:
    """возвращает сводку задач по статусам"""

    return service.get_summary_by_status()


@router.get("/export")
def export_tasks(
    status: TaskStatus | None = Query(default=None),
    author_id: int | None = Query(default=None, gt=0),
    assignee_id: int | None = Query(default=None, gt=0),
    sort_by: TaskSortField = Query(default=TaskSortField.UPDATED_AT),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
    service: TaskService = Depends(get_task_service),
) -> Response:
    """выгружает список задач в csv"""

    tasks = service.export_tasks(
        status=status,
        author_id=author_id,
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
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """возвращает задачу по идентификатору"""

    return service.get_task(task_id)


@router.get("/{task_id}/comments", response_model=list[CommentRead])
def list_task_comments(
    task_id: int,
    task_service: TaskService = Depends(get_task_service),
    comment_service: CommentService = Depends(get_comment_service),
) -> list[CommentRead]:
    """возвращает комментарии задачи"""

    task_service.get_task(task_id)
    return comment_service.list_comments(task_id=task_id)


@router.post("", response_model=TaskRead, status_code=201)
def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """создает задачу"""

    return service.create_task(payload)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """частично обновляет задачу"""

    return service.update_task(task_id=task_id, payload=payload)


@router.post("/{task_id}/assign", response_model=TaskRead)
def assign_task(
    task_id: int,
    payload: TaskAssign,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """назначает исполнителя задаче"""

    return service.assign_task(
        task_id=task_id, assignee_id=payload.assignee_id
    )


@router.post(
    "/{task_id}/comments", response_model=CommentRead, status_code=201
)
def create_task_comment(
    task_id: int,
    payload: TaskCommentCreate,
    task_service: TaskService = Depends(get_task_service),
    comment_service: CommentService = Depends(get_comment_service),
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
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """архивирует задачу"""

    return service.archive_task(task_id)


@router.patch("/{task_id}/status", response_model=TaskRead)
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """обновляет статус задачи"""

    return service.update_task_status(
        task_id=task_id,
        status=payload.status,
        changed_by_user_id=payload.changed_by_user_id,
    )
