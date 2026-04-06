from __future__ import annotations

from fastapi import APIRouter, Query

from app.dependencies.services import CommentServiceDep
from app.schemas.comments import CommentCreate, CommentRead

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("", response_model=list[CommentRead])
def list_comments(
    service: CommentServiceDep,
    task_id: int | None = Query(default=None, gt=0),
) -> list[CommentRead]:
    """возвращает комментарии с фильтром по задаче"""

    return service.list_comments(task_id=task_id)


@router.post("", response_model=CommentRead, status_code=201)
def create_comment(
    payload: CommentCreate,
    service: CommentServiceDep,
) -> CommentRead:
    """создает комментарий"""

    return service.create_comment(payload)
