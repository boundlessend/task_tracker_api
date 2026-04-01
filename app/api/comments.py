from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.repositories.comments import CommentRepository
from app.schemas.comments import CommentCreate, CommentRead
from app.services.comments import CommentService

router = APIRouter(prefix="/comments", tags=["comments"])


def get_comment_service(
    session: Session = Depends(get_db_session),
) -> CommentService:
    """создает сервис комментариев для запроса"""

    return CommentService(repository=CommentRepository(session=session))


@router.get("", response_model=list[CommentRead])
def list_comments(
    task_id: int | None = Query(default=None, gt=0),
    service: CommentService = Depends(get_comment_service),
) -> list[CommentRead]:
    """возвращает комментарии с фильтром по задаче"""

    return service.list_comments(task_id=task_id)


@router.post("", response_model=CommentRead, status_code=201)
def create_comment(
    payload: CommentCreate,
    service: CommentService = Depends(get_comment_service),
) -> CommentRead:
    """создает комментарий"""

    return service.create_comment(payload)
