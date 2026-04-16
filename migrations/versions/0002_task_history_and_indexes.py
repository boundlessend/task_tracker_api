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
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("changed_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
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
            ondelete="RESTRICT",
        ),
    )

    users_table = sa.table(
        "users",
        sa.column("username", sa.String(length=64)),
        sa.column("full_name", sa.String(length=255)),
    )
    op.execute(
        users_table.update()
        .where(
            sa.or_(
                users_table.c.full_name.is_(None),
                sa.func.trim(users_table.c.full_name) == "",
            )
        )
        .values(full_name=users_table.c.username)
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "full_name",
            existing_type=sa.String(length=255),
            nullable=False,
        )

    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint(
            "fk_tasks_author_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_tasks_assignee_id_users", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_tasks_author_id_users",
            "users",
            ["author_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_tasks_assignee_id_users",
            "users",
            ["assignee_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("comments") as batch_op:
        batch_op.drop_constraint(
            "fk_comments_author_id_users", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_comments_author_id_users",
            "users",
            ["author_id"],
            ["id"],
            ondelete="RESTRICT",
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
    op.drop_index("uq_users_email_lower", table_name="users")

    with op.batch_alter_table("comments") as batch_op:
        batch_op.drop_constraint(
            "fk_comments_author_id_users", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_comments_author_id_users",
            "users",
            ["author_id"],
            ["id"],
        )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint(
            "fk_tasks_author_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_tasks_assignee_id_users", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_tasks_author_id_users",
            "users",
            ["author_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_tasks_assignee_id_users",
            "users",
            ["assignee_id"],
            ["id"],
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "full_name",
            existing_type=sa.String(length=255),
            nullable=True,
        )

    op.drop_table("task_history")
