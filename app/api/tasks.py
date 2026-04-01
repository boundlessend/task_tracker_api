from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.repositories.tasks import TaskRepository
from app.schemas.tasks import (
    SortOrder,
    TaskCreate,
    TaskRead,
    TaskSortField,
    TaskStatus,
    TaskStatusUpdate,
    TaskSummaryByStatus,
)
from app.services.tasks import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(
    session: Session = Depends(get_db_session),
) -> TaskService:
    """создает сервис задач для запроса"""

    return TaskService(repository=TaskRepository(session=session))


@router.get("", response_model=list[TaskRead])
def list_tasks(
    status: TaskStatus | None = Query(default=None),
    author_id: int | None = Query(default=None, gt=0),
    assignee_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: TaskSortField = Query(default=TaskSortField.UPDATED_AT),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
    service: TaskService = Depends(get_task_service),
) -> list[TaskRead]:
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


@router.get("/summary/statuses", response_model=list[TaskSummaryByStatus])
def get_summary_by_status(
    service: TaskService = Depends(get_task_service),
) -> list[TaskSummaryByStatus]:
    """возвращает сводку задач по статусам"""

    return service.get_summary_by_status()


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """возвращает задачу по идентификатору"""

    return service.get_task(task_id)


@router.post("", response_model=TaskRead, status_code=201)
def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    """создает задачу"""

    return service.create_task(payload)


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
