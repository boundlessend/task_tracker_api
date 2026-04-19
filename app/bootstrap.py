from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.core.time import MOSCOW_TZ, to_storage_datetime
from app.db.models import Base, Comment, Task, TaskHistory, User
from app.db.session import get_engine, get_session_factory

logger = logging.getLogger(__name__)

DEMO_OWNER_ID = UUID("11111111-1111-4111-8111-111111111111")
DEMO_ASSIGNEE_ID = UUID("22222222-2222-4222-8222-222222222222")
DEMO_TASK_ID = UUID("33333333-3333-4333-8333-333333333333")
DEMO_COMMENT_ID = UUID("44444444-4444-4444-8444-444444444444")
DEMO_CREATED_HISTORY_ID = UUID("55555555-5555-4555-8555-555555555555")
DEMO_STATUS_HISTORY_ID = UUID("66666666-6666-4666-8666-666666666666")
DEMO_COMMENT_HISTORY_ID = UUID("77777777-7777-4777-8777-777777777777")


def prepare_application_data(settings: Settings) -> None:
    """подготавливает схему и демо-данные приложения"""

    engine = get_engine(settings)

    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)

    if not settings.seed_demo_data:
        return

    session = get_session_factory(settings)()
    try:
        if _has_data(session):
            return
        _seed_demo_data(session)
        session.commit()
        logger.info("добавлены демо-данные")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _has_data(session: Session) -> bool:
    """проверяет что база уже содержит данные"""

    users_total = session.scalar(select(func.count()).select_from(User))
    tasks_total = session.scalar(select(func.count()).select_from(Task))
    return int(users_total or 0) > 0 or int(tasks_total or 0) > 0


def _seed_demo_data(session: Session) -> None:
    """добавляет стартовые данные для локального запуска"""

    created_at = datetime(2026, 4, 3, 10, 0, tzinfo=MOSCOW_TZ)
    assigned_at = datetime(2026, 4, 3, 10, 5, tzinfo=MOSCOW_TZ)
    comment_created_at = datetime(2026, 4, 3, 10, 6, tzinfo=MOSCOW_TZ)

    _create_user(
        session,
        DEMO_OWNER_ID,
        "ivan",
        "ivan@example.com",
        "Ivan Ivanov",
        created_at,
    )
    _create_user(
        session,
        DEMO_ASSIGNEE_ID,
        "anna",
        "anna@example.com",
        "Anna Smirnova",
        created_at,
    )
    _create_task(
        session,
        DEMO_TASK_ID,
        "Подготовить api note",
        "Согласовать контракт",
        DEMO_OWNER_ID,
        DEMO_ASSIGNEE_ID,
        "in_progress",
        created_at,
        assigned_at,
    )
    _create_comment(
        session,
        DEMO_COMMENT_ID,
        DEMO_TASK_ID,
        DEMO_OWNER_ID,
        "Первый комментарий",
        comment_created_at,
    )
    _create_history_entry(
        session,
        DEMO_CREATED_HISTORY_ID,
        DEMO_TASK_ID,
        DEMO_OWNER_ID,
        "created",
        created_at,
        new_status="todo",
    )
    _create_history_entry(
        session,
        DEMO_STATUS_HISTORY_ID,
        DEMO_TASK_ID,
        DEMO_ASSIGNEE_ID,
        "status_changed",
        assigned_at,
        old_status="todo",
        new_status="in_progress",
    )
    _create_history_entry(
        session,
        DEMO_COMMENT_HISTORY_ID,
        DEMO_TASK_ID,
        DEMO_OWNER_ID,
        "comment_added",
        comment_created_at,
        comment_text="Первый комментарий",
    )


def _create_user(
    session: Session,
    user_id: UUID,
    username: str,
    email: str,
    full_name: str,
    created_at: datetime,
) -> User:
    """создает демо-пользователя"""

    user = User(
        id=user_id,
        username=username,
        email=email,
        full_name=full_name,
        created_at=to_storage_datetime(created_at),
    )
    session.add(user)
    return user


def _create_task(
    session: Session,
    task_id: UUID,
    title: str,
    description: str | None,
    owner_id: UUID,
    assignee_id: UUID | None,
    status: str,
    created_at: datetime,
    updated_at: datetime,
) -> Task:
    """создает демо-задачу"""

    due_date = datetime(2026, 4, 20, 12, 0, tzinfo=MOSCOW_TZ)
    task = Task(
        id=task_id,
        title=title,
        description=description,
        owner_id=owner_id,
        assignee_id=assignee_id,
        status=status,
        created_at=to_storage_datetime(created_at),
        updated_at=to_storage_datetime(updated_at),
        due_date=to_storage_datetime(due_date),
    )
    session.add(task)
    return task


def _create_comment(
    session: Session,
    comment_id: UUID,
    task_id: UUID,
    author_id: UUID,
    text: str,
    created_at: datetime,
) -> Comment:
    """создает демо-комментарий"""

    comment = Comment(
        id=comment_id,
        task_id=task_id,
        author_id=author_id,
        text=text,
        created_at=to_storage_datetime(created_at),
        updated_at=to_storage_datetime(created_at),
    )
    session.add(comment)
    return comment


def _create_history_entry(
    session: Session,
    history_id: UUID,
    task_id: UUID,
    changed_by_user_id: UUID,
    action: str,
    created_at: datetime,
    old_status: str | None = None,
    new_status: str | None = None,
    comment_text: str | None = None,
) -> TaskHistory:
    """создает демо-запись истории задачи"""

    history_entry = TaskHistory(
        id=history_id,
        task_id=task_id,
        changed_by_user_id=changed_by_user_id,
        action=action,
        old_status=old_status,
        new_status=new_status,
        comment_text=comment_text,
        created_at=to_storage_datetime(created_at),
    )
    session.add(history_entry)
    return history_entry
