"""добавляет архивирование задач"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_task_archive"
down_revision: str | None = "0002_task_history_and_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """применяет миграцию архивирования задач"""

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column("archived_at", sa.DateTime(), nullable=True)
        )

    op.create_index("ix_tasks_archived_at", "tasks", ["archived_at"])


def downgrade() -> None:
    """откатывает миграцию архивирования задач"""

    op.drop_index("ix_tasks_archived_at", table_name="tasks")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("archived_at")
