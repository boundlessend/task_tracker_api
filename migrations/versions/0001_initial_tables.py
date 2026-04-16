"""создает первые таблицы проекта"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TASK_STATUSES = ("todo", "in_progress", "done")


def upgrade() -> None:
    """применяет первую миграцию"""

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="todo",
        ),
        sa.Column("author_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("assignee_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            f"status IN {TASK_STATUSES}",
            name="ck_tasks_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name="fk_tasks_author_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"], ["users.id"], name="fk_tasks_assignee_id_users"
        ),
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("author_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_comments_task_id_tasks",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name="fk_comments_author_id_users"
        ),
    )

    op.create_index("ix_tasks_author_id", "tasks", ["author_id"])
    op.create_index("ix_tasks_assignee_id", "tasks", ["assignee_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_comments_task_id", "comments", ["task_id"])


def downgrade() -> None:
    """откатывает первую миграцию"""

    op.drop_index("ix_comments_task_id", table_name="comments")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_assignee_id", table_name="tasks")
    op.drop_index("ix_tasks_author_id", table_name="tasks")
    op.drop_table("comments")
    op.drop_table("tasks")
    op.drop_table("users")
