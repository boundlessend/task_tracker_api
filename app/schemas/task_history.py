from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.users import UserRefRead


class TaskHistoryAction(str, Enum):
    """допустимые действия в истории задачи"""

    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    COMMENT_ADDED = "comment_added"


class TaskHistoryRead(BaseModel):
    """данные записи истории задачи"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    changed_by_user_id: UUID
    action: TaskHistoryAction
    old_status: str | None = None
    new_status: str | None = None
    comment_text: str | None = None
    created_at: datetime
    changed_by: UserRefRead
