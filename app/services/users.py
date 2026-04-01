from app.repositories.users import UserRepository
from app.schemas.users import UserCreate, UserRead


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
