from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """данные для создания комментария"""

    model_config = ConfigDict(extra="forbid")

    task_id: int = Field(gt=0)
    author_id: int = Field(gt=0)
    text: str = Field(min_length=1)


class TaskCommentCreate(BaseModel):
    """данные для создания комментария у задачи"""

    model_config = ConfigDict(extra="forbid")

    author_id: int = Field(gt=0)
    text: str = Field(min_length=1)


class CommentRead(BaseModel):
    """данные комментария из базы"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    author_username: str
    text: str
    created_at: datetime
