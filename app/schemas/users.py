from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """данные для создания пользователя"""

    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserRead(BaseModel):
    """данные пользователя из базы"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str
    created_at: datetime
