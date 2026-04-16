from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.time import from_storage_datetime
from app.db.models import Comment, Task, TaskHistory, User
from app.exceptions.errors import (
    CommentNotFoundError,
    DataIntegrityError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.schemas.comments import CommentCreate, CommentRead, CommentUpdate


class CommentRepository:
    """работает с комментариями через sqlalchemy"""

    def __init__(self, session: Session) -> None:
        """сохраняет сессию базы данных"""

        self.session = session

    def _ensure_task_exists(self, task_id: UUID) -> None:
        """проверяет что задача существует"""

        if self.session.get(Task, task_id) is None:
            raise TaskNotFoundError(
                f"Задача с id={task_id} не найдена.",
                details={"task_id": str(task_id)},
            )

    def _ensure_user_exists(self, user_id: UUID, field_name: str) -> None:
        """проверяет что пользователь существует"""

        if self.session.get(User, user_id) is None:
            raise UserNotFoundError(
                (
                    f"Пользователь для поля {field_name} "
                    f"с id={user_id} не найден."
                ),
                details={"field": field_name, "user_id": str(user_id)},
            )

    @staticmethod
    def _map_comment(comment: Comment) -> CommentRead:
        """преобразует orm-модель комментария в схему"""

        return CommentRead.model_validate(
            {
                "id": comment.id,
                "task_id": comment.task_id,
                "author_id": comment.author_id,
                "text": comment.text,
                "created_at": from_storage_datetime(comment.created_at),
                "updated_at": from_storage_datetime(comment.updated_at),
                "author": {
                    "id": comment.author.id,
                    "username": comment.author.username,
                    "full_name": comment.author.full_name,
                },
            }
        )

    def _get_comment_model(self, comment_id: UUID) -> Comment:
        """возвращает orm-модель комментария"""

        comment = self.session.scalar(
            select(Comment)
            .where(Comment.id == comment_id)
            .options(joinedload(Comment.author))
        )
        if comment is None:
            raise CommentNotFoundError(
                f"Комментарий с id={comment_id} не найден.",
                details={"comment_id": str(comment_id)},
            )
        return comment

    def get_comment(self, comment_id: UUID) -> CommentRead:
        """возвращает комментарий по идентификатору"""

        return self._map_comment(self._get_comment_model(comment_id))

    def create_comment(self, payload: CommentCreate) -> CommentRead:
        """создает комментарий и возвращает его"""

        self._ensure_task_exists(payload.task_id)
        self._ensure_user_exists(payload.author_id, "author_id")

        comment = Comment(**payload.model_dump())
        history_entry = TaskHistory(
            task_id=payload.task_id,
            changed_by_user_id=payload.author_id,
            action="comment_added",
            comment_text=payload.text,
        )
        self.session.add(comment)
        self.session.add(history_entry)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось создать комментарий. "
                "Проверьте task_id и author_id."
            ) from exc
        return self.get_comment(comment.id)

    def list_comments(self, task_id: UUID | None = None) -> list[CommentRead]:
        """возвращает комментарии с необязательным фильтром по задаче"""

        query = (
            select(Comment)
            .options(joinedload(Comment.author))
            .order_by(Comment.created_at.asc(), Comment.id.asc())
        )
        if task_id is not None:
            query = query.where(Comment.task_id == task_id)
        comments = self.session.scalars(query).all()
        return [self._map_comment(comment) for comment in comments]

    def update_comment(
        self,
        comment_id: UUID,
        payload: CommentUpdate,
    ) -> CommentRead:
        """частично обновляет комментарий"""

        comment = self._get_comment_model(comment_id)
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self._map_comment(comment)

        for field_name, value in updates.items():
            setattr(comment, field_name, value)

        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось обновить комментарий. Проверьте ограничения полей."
            ) from exc
        return self.get_comment(comment_id)
