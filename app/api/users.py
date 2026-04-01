from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.repositories.users import UserRepository
from app.schemas.users import UserCreate, UserRead
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(
    session: Session = Depends(get_db_session),
) -> UserService:
    """создает сервис пользователей для запроса"""

    return UserService(repository=UserRepository(session=session))


@router.get("", response_model=list[UserRead])
def list_users(
    service: UserService = Depends(get_user_service),
) -> list[UserRead]:
    """возвращает список пользователей"""

    return service.list_users()


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    """создает пользователя"""

    return service.create_user(payload)
