from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DataIntegrityError
from app.schemas.users import UserCreate, UserRead


class UserRepository:
    """работает с пользователями через sql"""

    def __init__(self, session: Session) -> None:
        """сохраняет сессию базы данных"""

        self.session = session

    def create_user(self, payload: UserCreate) -> UserRead:
        """создает пользователя в базе"""

        query = text(
            """
            INSERT INTO users (username, email, full_name)
            VALUES (:username, :email, :full_name)
            RETURNING id, username, email, full_name, created_at
            """
        )
        try:
            row = (
                self.session.execute(query, payload.model_dump())
                .mappings()
                .one()
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось создать пользователя. "
                "Проверьте уникальность username и email."
            ) from exc
        return UserRead.model_validate(row)

    def list_users(self) -> list[UserRead]:
        """возвращает список пользователей"""

        query = text(
            """
            SELECT id, username, email, full_name, created_at
            FROM users
            ORDER BY created_at DESC, id DESC
            """
        )
        rows = self.session.execute(query).mappings().all()
        return [UserRead.model_validate(row) for row in rows]
