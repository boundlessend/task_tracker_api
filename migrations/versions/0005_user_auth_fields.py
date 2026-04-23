"""добавляет роли и признак активности пользователей"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_user_auth_fields"
down_revision: str | None = "0004_task_owner_comment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_ROLES = ("user", "admin")


def upgrade() -> None:
    """применяет миграцию полей аутентификации пользователя"""

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=32),
                nullable=False,
                server_default="user",
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.create_check_constraint(
            "ck_users_role_allowed",
            f"role IN {USER_ROLES}",
        )


def downgrade() -> None:
    """откатывает миграцию полей аутентификации пользователя"""

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role_allowed", type_="check")
        batch_op.drop_column("is_active")
        batch_op.drop_column("role")
