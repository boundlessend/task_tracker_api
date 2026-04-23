from __future__ import annotations

from uuid import UUID

from app.exceptions.errors import ForbiddenError
from app.schemas.tasks import TaskRead
from app.schemas.users import CurrentUser, UserRole


def ensure_admin(current_user: CurrentUser) -> None:
    """проверяет что текущий пользователь администратор"""

    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError(
            "доступ разрешен только администратору",
            details={"required_role": UserRole.ADMIN.value},
        )


def ensure_owner_or_admin(task: TaskRead, current_user: CurrentUser) -> None:
    """проверяет правило owner/admin для задачи"""

    if current_user.role == UserRole.ADMIN:
        return
    if task.owner_id != current_user.id:
        raise ForbiddenError(
            "доступ к чужой задаче запрещен",
            details={"task_id": str(task.id), "rule": "owner_or_admin"},
        )


def ensure_assignment_allowed(
    assignee_id: UUID,
    current_user: CurrentUser,
) -> None:
    """проверяет допустимость назначения исполнителя"""

    if current_user.role == UserRole.ADMIN:
        return
    if assignee_id != current_user.id:
        raise ForbiddenError(
            "обычный пользователь может назначить исполнителем только себя",
            details={
                "assignee_id": str(assignee_id),
                "rule": "self_assign_or_admin",
            },
        )
