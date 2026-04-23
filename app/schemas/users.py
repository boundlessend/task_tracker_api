from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    """доступные роли пользователя"""

    USER = "user"
    ADMIN = "admin"


class UserCreate(BaseModel):
    """данные для создания пользователя"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "username": "ivan",
                "email": "ivan@example.com",
                "full_name": "Иван Петров",
                "role": "user",
            }
        },
    )

    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.USER


class UserRefRead(BaseModel):
    """краткие данные связанного пользователя"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str


class CurrentUser(BaseModel):
    """данные текущего пользователя из auth-контекста"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool


class UserRead(BaseModel):
    """данные пользователя из базы"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
