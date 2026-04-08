from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.errors import DataIntegrityError
from app.schemas.comments import CommentCreate, CommentRead


class CommentRepository:
    """работает с комментариями через sql"""

    def __init__(self, session: Session) -> None:
        """сохраняет сессию базы данных"""

        self.session = session

    def create_comment(self, payload: CommentCreate) -> CommentRead:
        """создает комментарий и возвращает его"""

        insert_comment = text(
            """
            INSERT INTO comments (task_id, author_id, text)
            VALUES (:task_id, :author_id, :text)
            RETURNING id, task_id, author_id, text, created_at
            """
        )
        select_comment = text(
            """
            SELECT
                c.id,
                c.task_id,
                c.author_id,
                u.username AS author_username,
                c.text,
                c.created_at
            FROM comments c
            JOIN users u ON u.id = c.author_id
            WHERE c.id = :comment_id
            """
        )
        insert_history = text(
            """
            INSERT INTO task_history (
                task_id,
                changed_by_user_id,
                action,
                comment_text
            )
            VALUES (:task_id, :changed_by_user_id, 'comment_added', :comment_text)
            """
        )
        try:
            comment_row = (
                self.session.execute(insert_comment, payload.model_dump())
                .mappings()
                .one()
            )
            self.session.execute(
                insert_history,
                {
                    "task_id": payload.task_id,
                    "changed_by_user_id": payload.author_id,
                    "comment_text": payload.text,
                },
            )
            comment = (
                self.session.execute(
                    select_comment, {"comment_id": comment_row["id"]}
                )
                .mappings()
                .one()
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось создать комментарий. Проверьте task_id и author_id."
            ) from exc
        return CommentRead.model_validate(comment)

    def list_comments(self, task_id: int | None = None) -> list[CommentRead]:
        """возвращает комментарии с необязательным фильтром по задаче"""

        query_text = """
            SELECT
                c.id,
                c.task_id,
                c.author_id,
                u.username AS author_username,
                c.text,
                c.created_at
            FROM comments c
            JOIN users u ON u.id = c.author_id
        """
        params: dict[str, object] = {}
        if task_id is not None:
            query_text += " WHERE c.task_id = :task_id"
            params["task_id"] = task_id
        query_text += " ORDER BY c.created_at ASC, c.id ASC"
        rows = self.session.execute(text(query_text), params).mappings().all()
        return [CommentRead.model_validate(row) for row in rows]
