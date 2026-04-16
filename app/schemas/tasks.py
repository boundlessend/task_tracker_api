from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.comments import CommentRead
from app.schemas.task_history import TaskHistoryRead
from app.schemas.users import UserRefRead


class TaskStatus(str, Enum):
    """допустимые статусы задачи"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskSortField(str, Enum):
    """поля сортировки списка задач"""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(str, Enum):
    """допустимые направления сортировки"""

    ASC = "asc"
    DESC = "desc"


class TaskCreate(BaseModel):
    """данные для создания задачи"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "title": "Подготовить api note",
                "description": "Согласовать контракт ручек",
                "owner_id": "11111111-1111-4111-8111-111111111111",
                "assignee_id": "22222222-2222-4222-8222-222222222222",
                "status": "todo",
                "due_date": "2026-04-20T12:00:00+03:00",
            }
        },
    )

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    owner_id: UUID
    assignee_id: UUID | None = None
    status: TaskStatus = TaskStatus.TODO
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    """данные для частичного обновления задачи"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "TaskUpdate":
        """проверяет ограничения частичного обновления"""

        if not self.model_fields_set:
            raise ValueError(
                "Нужно передать хотя бы одно поле для обновления."
            )
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Поле title не может быть null.")
        return self


class TaskAssign(BaseModel):
    """данные для назначения исполнителя"""

    model_config = ConfigDict(extra="forbid")

    assignee_id: UUID


class TaskClose(BaseModel):
    """данные для закрытия задачи"""

    model_config = ConfigDict(extra="forbid")

    changed_by_user_id: UUID


class TaskStatusUpdate(BaseModel):
    """данные для изменения статуса задачи"""

    model_config = ConfigDict(extra="forbid")

    status: TaskStatus
    changed_by_user_id: UUID


class TaskListItemRead(BaseModel):
    """данные задачи для списков и поиска"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    status: TaskStatus
    owner_id: UUID
    assignee_id: UUID | None = None
    due_date: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    comment_count: int = 0
    owner: UserRefRead
    assignee: UserRefRead | None = None


class TaskRead(TaskListItemRead):
    """полные данные задачи со связанными сущностями"""

    comments: list[CommentRead] = Field(default_factory=list)
    history: list[TaskHistoryRead] = Field(default_factory=list)


class TaskListMeta(BaseModel):
    """метаданные списка задач"""

    limit: int
    offset: int
    count: int
    total: int


class TaskListResponse(BaseModel):
    """ответ со списком задач"""

    items: list[TaskListItemRead]
    meta: TaskListMeta


class TaskSummaryByStatus(BaseModel):
    """агрегированная сводка по статусу"""

    status: TaskStatus
    task_count: int


class TaskSummaryRead(BaseModel):
    """сводка по задачам"""

    total: int
    archived: int
    by_status: list[TaskSummaryByStatus]
