from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    """допустимые статусы задачи"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskSortField(str, Enum):
    """поля сортировки под реальные индексы списка задач"""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(str, Enum):
    """допустимые направления сортировки"""

    ASC = "asc"
    DESC = "desc"


class TaskCreate(BaseModel):
    """данные для создания задачи"""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    author_id: int = Field(gt=0)
    assignee_id: int | None = Field(default=None, gt=0)
    status: TaskStatus = TaskStatus.TODO
    due_date: datetime | None = None


class TaskStatusUpdate(BaseModel):
    """данные для изменения статуса задачи"""

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
    created_at: datetime
    updated_at: datetime
    comment_count: int = 0


class TaskSummaryByStatus(BaseModel):
    """агрегированная сводка по статусу"""

    status: TaskStatus
    task_count: int
