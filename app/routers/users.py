from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies.auth import CurrentUserDep, get_current_user
from app.dependencies.services import UserServiceDep
from app.schemas.users import UserCreate, UserRead
from app.services.access import ensure_admin

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


@router.post("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: UUID,
    service: UserServiceDep,
    current_user: CurrentUserDep = Depends(get_current_user),
) -> UserRead:
    """деактивирует пользователя"""

    ensure_admin(current_user)
    return service.deactivate_user(user_id)
