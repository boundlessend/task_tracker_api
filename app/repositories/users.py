from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import from_storage_datetime
from app.db.models import User
from app.exceptions.errors import DataIntegrityError, UserNotFoundError
from app.schemas.users import CurrentUser, UserCreate, UserRead


class UserRepository:
    """работает с пользователями через sqlalchemy"""

    def __init__(self, session: Session) -> None:
        """сохраняет сессию базы данных"""

        self.session = session

    @staticmethod
    def _map_user(user: User) -> UserRead:
        """преобразует orm-модель пользователя в схему"""

        return UserRead.model_validate(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": from_storage_datetime(user.created_at),
            }
        )

    @staticmethod
    def _map_current_user(user: User) -> CurrentUser:
        """преобразует orm-модель пользователя в auth-схему"""

        return CurrentUser.model_validate(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
            }
        )

    def get_user_model(self, user_id: UUID) -> User | None:
        """возвращает orm-модель пользователя по id"""

        return self.session.get(User, user_id)

    def get_user_model_by_username(self, username: str) -> User | None:
        """возвращает orm-модель пользователя по username"""

        return self.session.scalar(select(User).where(User.username == username))

    def get_current_user_by_username(self, username: str) -> CurrentUser | None:
        """возвращает текущего пользователя по username"""

        user = self.get_user_model_by_username(username)
        if user is None:
            return None
        return self._map_current_user(user)

    def create_user(self, payload: UserCreate) -> UserRead:
        """создает пользователя в базе"""

        user = User(**payload.model_dump())
        self.session.add(user)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось создать пользователя. "
                "Проверьте уникальность username и email."
            ) from exc
        self.session.refresh(user)
        return self._map_user(user)

    def list_users(self) -> list[UserRead]:
        """возвращает список пользователей"""

        users = self.session.scalars(
            select(User).order_by(User.created_at.desc(), User.id.desc())
        ).all()
        return [self._map_user(user) for user in users]

    def deactivate_user(self, user_id: UUID) -> UserRead:
        """деактивирует пользователя"""

        user = self.get_user_model(user_id)
        if user is None:
            raise UserNotFoundError(
                f"Пользователь с id={user_id} не найден.",
                details={"user_id": str(user_id)},
            )
        if not user.is_active:
            return self._map_user(user)

        user.is_active = False
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось деактивировать пользователя."
            ) from exc
        self.session.refresh(user)
        return self._map_user(user)
