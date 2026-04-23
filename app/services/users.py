from uuid import UUID

from app.exceptions.errors import AuthenticationError, InactiveUserError
from app.repositories.users import UserRepository
from app.schemas.auth import LoginResponse
from app.schemas.users import CurrentUser, UserCreate, UserRead

STUB_TOKEN_PREFIX = "stub:"


class UserService:
    """содержит сценарии работы с пользователями"""

    def __init__(self, repository: UserRepository) -> None:
        """сохраняет репозиторий пользователей"""

        self.repository = repository

    def create_user(self, payload: UserCreate) -> UserRead:
        """создает пользователя"""

        return self.repository.create_user(payload)

    def list_users(self) -> list[UserRead]:
        """возвращает список пользователей"""

        return self.repository.list_users()

    def get_current_user_by_username(self, username: str) -> CurrentUser:
        """возвращает активного пользователя по username"""

        user = self.repository.get_current_user_by_username(username)
        if user is None:
            raise AuthenticationError(
                "пользователь из auth-заголовка не найден",
                details={"username": username},
            )
        if not user.is_active:
            raise InactiveUserError(
                "аккаунт деактивирован",
                details={"user_id": str(user.id)},
            )
        return user

    def login(self, username: str) -> LoginResponse:
        """выполняет учебный логин по username"""

        current_user = self.get_current_user_by_username(username)
        return LoginResponse(
            access_token=f"{STUB_TOKEN_PREFIX}{current_user.username}",
            current_user=current_user,
        )

    def deactivate_user(self, user_id: UUID) -> UserRead:
        """деактивирует пользователя"""

        return self.repository.deactivate_user(user_id)
