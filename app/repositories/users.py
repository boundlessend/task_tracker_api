from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import from_storage_datetime
from app.db.models import User
from app.exceptions.errors import DataIntegrityError
from app.schemas.users import UserCreate, UserRead


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
                "created_at": from_storage_datetime(user.created_at),
            }
        )

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
