from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db_session
from app.repositories.comments import CommentRepository
from app.repositories.tasks import TaskRepository
from app.repositories.users import UserRepository
from app.services.comments import CommentService
from app.services.tasks import TaskService
from app.services.users import UserService


SessionDep = Annotated[Session, Depends(get_db_session)]


def get_task_service(session: SessionDep) -> TaskService:
    """создает сервис задач для запроса"""

    return TaskService(repository=TaskRepository(session=session))


def get_comment_service(session: SessionDep) -> CommentService:
    """создает сервис комментариев для запроса"""

    return CommentService(repository=CommentRepository(session=session))


def get_user_service(session: SessionDep) -> UserService:
    """создает сервис пользователей для запроса"""

    return UserService(repository=UserRepository(session=session))


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
