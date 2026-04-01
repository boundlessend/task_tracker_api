"""добавляет историю задач и усиливает схему"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_task_history_and_indexes"
down_revision: str | None = "0001_initial_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HISTORY_ACTIONS = ("created", "status_changed", "comment_added")


def upgrade() -> None:
    """применяет вторую миграцию"""

    op.create_table(
        "task_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("old_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=True),
        sa.Column("comment_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            f"action IN {HISTORY_ACTIONS}",
            name="ck_task_history_action_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_task_history_task_id_tasks",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
            name="fk_task_history_changed_by_user_id_users",
        ),
    )

    op.create_index(
        "ix_tasks_status_created_at",
        "tasks",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_tasks_status_updated_at",
        "tasks",
        ["status", "updated_at"],
    )
    op.create_index(
        "ix_tasks_author_status_created_at",
        "tasks",
        ["author_id", "status", "created_at"],
    )
    op.create_index(
        "ix_tasks_author_status_updated_at",
        "tasks",
        ["author_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_tasks_assignee_status_created_at",
        "tasks",
        ["assignee_id", "status", "created_at"],
    )
    op.create_index(
        "ix_tasks_assignee_status_updated_at",
        "tasks",
        ["assignee_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_comments_task_id_created_at",
        "comments",
        ["task_id", "created_at"],
    )
    op.create_index(
        "ix_task_history_task_id_created_at",
        "task_history",
        ["task_id", "created_at"],
    )


def downgrade() -> None:
    """откатывает вторую миграцию"""

    op.drop_index(
        "ix_task_history_task_id_created_at", table_name="task_history"
    )
    op.drop_index("ix_comments_task_id_created_at", table_name="comments")
    op.drop_index("ix_tasks_assignee_status_updated_at", table_name="tasks")
    op.drop_index("ix_tasks_assignee_status_created_at", table_name="tasks")
    op.drop_index("ix_tasks_author_status_updated_at", table_name="tasks")
    op.drop_index("ix_tasks_author_status_created_at", table_name="tasks")
    op.drop_index("ix_tasks_status_updated_at", table_name="tasks")
    op.drop_index("ix_tasks_status_created_at", table_name="tasks")
    op.drop_table("task_history")
