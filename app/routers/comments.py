from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies.services import CommentServiceDep
from app.schemas.comments import CommentCreate, CommentRead, CommentUpdate

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("", response_model=list[CommentRead])
def list_comments(
    service: CommentServiceDep,
    task_id: UUID | None = Query(default=None),
) -> list[CommentRead]:
    """возвращает комментарии с фильтром по задаче"""

    return service.list_comments(task_id=task_id)


@router.get("/{comment_id}", response_model=CommentRead)
def get_comment(
    comment_id: UUID,
    service: CommentServiceDep,
) -> CommentRead:
    """возвращает комментарий по идентификатору"""

    return service.get_comment(comment_id)


@router.post("", response_model=CommentRead, status_code=201)
def create_comment(
    payload: CommentCreate,
    service: CommentServiceDep,
) -> CommentRead:
    """создает комментарий"""

    return service.create_comment(payload)


@router.patch("/{comment_id}", response_model=CommentRead)
def update_comment(
    comment_id: UUID,
    payload: CommentUpdate,
    service: CommentServiceDep,
) -> CommentRead:
    """частично обновляет комментарий"""

    return service.update_comment(comment_id=comment_id, payload=payload)
