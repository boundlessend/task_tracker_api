from __future__ import annotations

from app.repositories.comments import CommentRepository
from app.schemas.comments import CommentCreate, CommentRead


class CommentService:
    """содержит сценарии работы с комментариями"""

    def __init__(self, repository: CommentRepository) -> None:
        """сохраняет репозиторий комментариев"""

        self.repository = repository

    def create_comment(self, payload: CommentCreate) -> CommentRead:
        """создает комментарий"""

        return self.repository.create_comment(payload)

    def list_comments(self, task_id: int | None = None) -> list[CommentRead]:
        """возвращает список комментариев"""

        return self.repository.list_comments(task_id=task_id)
