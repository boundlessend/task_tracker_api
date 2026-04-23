from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.users import UserRefRead


class CommentCreate(BaseModel):
    """внутренние данные для создания комментария"""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    author_id: UUID
    text: str = Field(min_length=1)


class TaskCommentCreate(BaseModel):
    """данные для создания комментария у задачи"""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)


class CommentCreateRequest(BaseModel):
    """данные запроса на создание комментария"""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    text: str = Field(min_length=1)


class CommentUpdate(BaseModel):
    """данные для частичного обновления комментария"""

    model_config = ConfigDict(extra="forbid")

    text: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_payload(self) -> "CommentUpdate":
        """проверяет ограничения частичного обновления"""

        if not self.model_fields_set:
            raise ValueError(
                "Нужно передать хотя бы одно поле для обновления."
            )
        if "text" in self.model_fields_set and self.text is None:
            raise ValueError("Поле text не может быть null.")
        return self


class CommentRead(BaseModel):
    """данные комментария из базы"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    author_id: UUID
    text: str
    created_at: datetime
    updated_at: datetime
    author: UserRefRead
