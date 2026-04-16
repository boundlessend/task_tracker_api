"""приводит модель задач и комментариев к новой схеме"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_task_owner_comment"
down_revision: str | None = "0003_task_archive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """применяет миграцию новой модели задач и комментариев"""

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "author_id",
            new_column_name="owner_id",
            existing_type=sa.Uuid(as_uuid=True),
            existing_nullable=False,
        )
        batch_op.add_column(
            sa.Column("closed_at", sa.DateTime(), nullable=True)
        )

    tasks_table = sa.table(
        "tasks",
        sa.column("status", sa.String(length=32)),
        sa.column("updated_at", sa.DateTime()),
        sa.column("closed_at", sa.DateTime()),
    )
    op.execute(
        tasks_table.update()
        .where(
            sa.and_(
                tasks_table.c.status == "done",
                tasks_table.c.closed_at.is_(None),
            )
        )
        .values(closed_at=tasks_table.c.updated_at)
    )
    op.create_index("ix_tasks_closed_at", "tasks", ["closed_at"])

    with op.batch_alter_table("comments") as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )

    comments_table = sa.table(
        "comments",
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    op.execute(
        comments_table.update()
        .where(comments_table.c.updated_at.is_(None))
        .values(updated_at=comments_table.c.created_at)
    )


def downgrade() -> None:
    """откатывает миграцию новой модели задач и комментариев"""

    with op.batch_alter_table("comments") as batch_op:
        batch_op.drop_column("updated_at")

    op.drop_index("ix_tasks_closed_at", table_name="tasks")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("closed_at")
        batch_op.alter_column(
            "owner_id",
            new_column_name="author_id",
            existing_type=sa.Uuid(as_uuid=True),
            existing_nullable=False,
        )
