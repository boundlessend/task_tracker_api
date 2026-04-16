from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.time import now_msk, to_storage_datetime

TASK_STATUSES = ("todo", "in_progress", "done")
TASK_HISTORY_ACTIONS = ("created", "status_changed", "comment_added")


class Base(DeclarativeBase):
    """базовый класс orm-моделей"""


class User(Base):
    """orm-модель пользователя"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=lambda: to_storage_datetime(now_msk()),
    )

    owned_tasks: Mapped[list[Task]] = relationship(
        back_populates="owner",
        foreign_keys="Task.owner_id",
    )
    assigned_tasks: Mapped[list[Task]] = relationship(
        back_populates="assignee",
        foreign_keys="Task.assignee_id",
    )
    comments: Mapped[list[Comment]] = relationship(back_populates="author")
    history_entries: Mapped[list[TaskHistory]] = relationship(
        back_populates="changed_by"
    )


class Task(Base):
    """orm-модель задачи"""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            f"status IN {TASK_STATUSES}",
            name="ck_tasks_status_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="todo",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=lambda: to_storage_datetime(now_msk()),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=lambda: to_storage_datetime(now_msk()),
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    owner: Mapped[User] = relationship(
        back_populates="owned_tasks",
        foreign_keys=[owner_id],
    )
    assignee: Mapped[User | None] = relationship(
        back_populates="assigned_tasks",
        foreign_keys=[assignee_id],
    )
    comments: Mapped[list[Comment]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by=lambda: (Comment.created_at.asc(), Comment.id.asc()),
    )
    history: Mapped[list[TaskHistory]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by=lambda: (TaskHistory.created_at.asc(), TaskHistory.id.asc()),
    )


class Comment(Base):
    """orm-модель комментария"""

    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=lambda: to_storage_datetime(now_msk()),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=lambda: to_storage_datetime(now_msk()),
    )

    task: Mapped[Task] = relationship(back_populates="comments")
    author: Mapped[User] = relationship(back_populates="comments")


class TaskHistory(Base):
    """orm-модель истории задачи"""

    __tablename__ = "task_history"
    __table_args__ = (
        CheckConstraint(
            f"action IN {TASK_HISTORY_ACTIONS}",
            name="ck_task_history_action_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    comment_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=lambda: to_storage_datetime(now_msk()),
    )

    task: Mapped[Task] = relationship(back_populates="history")
    changed_by: Mapped[User] = relationship(back_populates="history_entries")
