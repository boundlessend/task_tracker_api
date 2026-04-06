from __future__ import annotations

from fastapi import APIRouter

from app.dependencies.services import UserServiceDep
from app.schemas.users import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    service: UserServiceDep,
) -> list[UserRead]:
    """возвращает список пользователей"""

    return service.list_users()


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    service: UserServiceDep,
) -> UserRead:
    """создает пользователя"""

    return service.create_user(payload)
