from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    author_id: int = Field(gt=0)
    assignee_id: int | None = Field(default=None, gt=0)
    status: TaskStatus = TaskStatus.TODO
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    """данные для частичного обновления задачи"""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None

    @model_validator(mode="after")
    def validate_nullable_fields(self) -> "TaskUpdate":
        """проверяет поля которые нельзя передавать как null"""

        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Поле title не может быть null.")
        return self


class TaskAssign(BaseModel):
    """данные для назначения исполнителя"""

    model_config = ConfigDict(extra="forbid")

    assignee_id: int = Field(gt=0)


class TaskClose(BaseModel):
    """данные для закрытия задачи"""

    model_config = ConfigDict(extra="forbid")

    changed_by_user_id: int = Field(gt=0)


class TaskStatusUpdate(BaseModel):
    """данные для изменения статуса задачи"""

    model_config = ConfigDict(extra="forbid")

    status: TaskStatus
    changed_by_user_id: int = Field(gt=0)


class TaskRead(BaseModel):
    """данные задачи из базы"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    status: TaskStatus
    author_id: int
    assignee_id: int | None = None
    author_username: str
    assignee_username: str | None = None
    due_date: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    comment_count: int = 0


class TaskListMeta(BaseModel):
    """метаданные списка задач"""

    limit: int
    offset: int
    count: int
    total: int


class TaskListResponse(BaseModel):
    """ответ со списком задач"""

    items: list[TaskRead]
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
