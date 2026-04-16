from __future__ import annotations

from uuid import UUID

from app.repositories.comments import CommentRepository
from app.schemas.comments import CommentCreate, CommentRead, CommentUpdate


class CommentService:
    """содержит сценарии работы с комментариями"""

    def __init__(self, repository: CommentRepository) -> None:
        """сохраняет репозиторий комментариев"""

        self.repository = repository

    def get_comment(self, comment_id: UUID) -> CommentRead:
        """возвращает комментарий по идентификатору"""

        return self.repository.get_comment(comment_id)

    def create_comment(self, payload: CommentCreate) -> CommentRead:
        """создает комментарий"""

        return self.repository.create_comment(payload)

    def list_comments(self, task_id: UUID | None = None) -> list[CommentRead]:
        """возвращает список комментариев"""

        return self.repository.list_comments(task_id=task_id)

    def update_comment(
        self,
        comment_id: UUID,
        payload: CommentUpdate,
    ) -> CommentRead:
        """частично обновляет комментарий"""

        return self.repository.update_comment(
            comment_id=comment_id, payload=payload
        )
