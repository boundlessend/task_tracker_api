from pydantic import BaseModel, ConfigDict, Field

from app.schemas.users import CurrentUser


class LoginRequest(BaseModel):
    """данные для учебного логина"""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=64)


class LoginResponse(BaseModel):
    """ответ логина с учебным токеном"""

    access_token: str
    token_type: str = "bearer"
    current_user: CurrentUser
