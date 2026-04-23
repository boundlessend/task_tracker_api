from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import CurrentUserDep, get_current_user
from app.dependencies.services import CommentServiceDep, TaskServiceDep
from app.schemas.comments import (
    CommentCreate,
    CommentCreateRequest,
    CommentRead,
    CommentUpdate,
)
from app.schemas.users import UserRole
from app.services.access import ensure_admin

router = APIRouter(
    prefix="/comments",
    tags=["comments"],
    dependencies=[Depends(get_current_user)],
)


def _ensure_comment_access(
    comment: CommentRead,
    task_service: TaskServiceDep,
    current_user: CurrentUserDep,
) -> None:
    """проверяет доступ к комментарию"""

    if current_user.role == UserRole.ADMIN or comment.author_id == current_user.id:
        return
    task_service.get_task_for_user(comment.task_id, current_user)


@router.get("", response_model=list[CommentRead])
def list_comments(
    service: CommentServiceDep,
    task_service: TaskServiceDep,
    current_user: CurrentUserDep = Depends(get_current_user),
    task_id: UUID | None = Query(default=None),
) -> list[CommentRead]:
    """возвращает комментарии с фильтром по задаче"""

    if task_id is not None:
        task_service.get_task_for_user(task_id, current_user)
        return service.list_comments(task_id=task_id)

    ensure_admin(current_user)
    return service.list_comments(task_id=task_id)


@router.get("/{comment_id}", response_model=CommentRead)
def get_comment(
    comment_id: UUID,
    service: CommentServiceDep,
    task_service: TaskServiceDep,
    current_user: CurrentUserDep = Depends(get_current_user),
) -> CommentRead:
    """возвращает комментарий по идентификатору"""

    comment = service.get_comment(comment_id)
    _ensure_comment_access(comment, task_service, current_user)
    return comment


@router.post("", response_model=CommentRead, status_code=201)
def create_comment(
    payload: CommentCreateRequest,
    service: CommentServiceDep,
    task_service: TaskServiceDep,
    current_user: CurrentUserDep = Depends(get_current_user),
) -> CommentRead:
    """создает комментарий"""

    task_service.get_task_for_user(payload.task_id, current_user)
    return service.create_comment(
        CommentCreate(
            task_id=payload.task_id,
            author_id=current_user.id,
            text=payload.text,
        )
    )


@router.patch("/{comment_id}", response_model=CommentRead)
def update_comment(
    comment_id: UUID,
    payload: CommentUpdate,
    service: CommentServiceDep,
    task_service: TaskServiceDep,
    current_user: CurrentUserDep = Depends(get_current_user),
) -> CommentRead:
    """частично обновляет комментарий"""

    comment = service.get_comment(comment_id)
    _ensure_comment_access(comment, task_service, current_user)
    return service.update_comment(comment_id=comment_id, payload=payload)
