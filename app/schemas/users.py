from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """данные для создания пользователя"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "username": "ivan",
                "email": "ivan@example.com",
                "full_name": "Иван Петров",
            }
        },
    )

    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserRefRead(BaseModel):
    """краткие данные связанного пользователя"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str


class UserRead(BaseModel):
    """данные пользователя из базы"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    full_name: str
    created_at: datetime
