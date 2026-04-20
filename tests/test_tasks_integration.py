from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Comment, Task, TaskHistory, User
from app.repositories.tasks import TaskRepository
from app.schemas.tasks import TaskCreate, TaskStatus
from app.services.tasks import TaskService


def test_task_service_status_change_creates_task_history(
    db_session: Session,
) -> None:
    """проверяет сервисный сценарий смены статуса и запись в историю"""

    owner = User(
        username="service_owner",
        email="service_owner@example.com",
        full_name="Service Owner",
    )
    db_session.add(owner)
    db_session.commit()

    service = TaskService(repository=TaskRepository(session=db_session))
    created_task = service.create_task(
        TaskCreate(
            title="Сервисная задача",
            description="Проверить смену статуса",
            owner_id=owner.id,
            status=TaskStatus.TODO,
        )
    )

    updated_task = service.update_task_status(
        task_id=created_task.id,
        status=TaskStatus.DONE,
        changed_by_user_id=owner.id,
    )

    history_rows = db_session.scalars(
        select(TaskHistory)
        .where(TaskHistory.task_id == created_task.id)
        .order_by(TaskHistory.created_at.asc(), TaskHistory.id.asc())
    ).all()

    assert updated_task.status is TaskStatus.DONE
    assert updated_task.closed_at is not None
    assert [row.action for row in history_rows] == [
        "created",
        "status_changed",
    ]
    assert history_rows[-1].old_status == "todo"
    assert history_rows[-1].new_status == "done"


def test_task_orm_relations_persist_comment_and_history(
    db_session: Session,
) -> None:
    """проверяет orm-сценарий со связанными комментариями и историей"""

    owner = User(
        username="orm_owner",
        email="orm_owner@example.com",
        full_name="Orm Owner",
    )
    task = Task(
        title="ORM задача",
        description="Проверить загрузку связей",
        owner=owner,
        status="todo",
    )
    comment = Comment(task=task, author=owner, text="ORM комментарий")
    history_entry = TaskHistory(
        task=task,
        changed_by=owner,
        action="created",
        new_status="todo",
    )
    db_session.add_all([owner, task, comment, history_entry])
    db_session.commit()
    db_session.expire_all()

    persisted_task = db_session.scalar(
        select(Task)
        .where(Task.id == task.id)
        .options(
            selectinload(Task.comments).selectinload(Comment.author),
            selectinload(Task.history).selectinload(TaskHistory.changed_by),
        )
    )

    assert persisted_task is not None
    assert persisted_task.owner.username == "orm_owner"
    assert len(persisted_task.comments) == 1
    assert persisted_task.comments[0].text == "ORM комментарий"
    assert persisted_task.comments[0].author.email == "orm_owner@example.com"
    assert len(persisted_task.history) == 1
    assert persisted_task.history[0].action == "created"
    assert persisted_task.history[0].changed_by.username == "orm_owner"
