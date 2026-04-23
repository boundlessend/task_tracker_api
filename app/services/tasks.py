from __future__ import annotations

from uuid import UUID

from app.repositories.tasks import TaskRepository
from app.schemas.tasks import (
    SortOrder,
    TaskCreate,
    TaskListItemRead,
    TaskListResponse,
    TaskRead,
    TaskSortField,
    TaskStatus,
    TaskSummaryByStatus,
    TaskSummaryRead,
    TaskUpdate,
)
from app.schemas.users import CurrentUser
from app.services.access import ensure_assignment_allowed, ensure_owner_or_admin


class TaskService:
    """содержит сценарии работы с задачами"""

    def __init__(self, repository: TaskRepository) -> None:
        """сохраняет репозиторий задач"""

        self.repository = repository

    def create_task(self, payload: TaskCreate) -> TaskRead:
        """создает задачу"""

        return self.repository.create_task(payload)

    def get_task(self, task_id: UUID) -> TaskRead:
        """возвращает задачу по идентификатору"""

        return self.repository.get_task(task_id)

    def get_task_for_user(
        self,
        task_id: UUID,
        current_user: CurrentUser,
    ) -> TaskRead:
        """возвращает задачу если доступ разрешен"""

        task = self.get_task(task_id)
        ensure_owner_or_admin(task, current_user)
        return task

    def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        owner_id: UUID | None = None,
        assignee_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: TaskSortField = TaskSortField.UPDATED_AT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> TaskListResponse:
        """возвращает список задач"""

        return self.repository.list_tasks(
            status=status,
            owner_id=owner_id,
            assignee_id=assignee_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def search_tasks(
        self,
        query_text: str,
        limit: int = 20,
    ) -> list[TaskListItemRead]:
        """ищет задачи"""

        return self.repository.search_tasks(query_text=query_text, limit=limit)

    def export_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        owner_id: UUID | None = None,
        assignee_id: UUID | None = None,
        sort_by: TaskSortField = TaskSortField.UPDATED_AT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> list[TaskListItemRead]:
        """возвращает задачи для выгрузки"""

        return self.repository.export_tasks(
            status=status,
            owner_id=owner_id,
            assignee_id=assignee_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def get_summary(self) -> TaskSummaryRead:
        """возвращает сводку по задачам"""

        return self.repository.get_summary()

    def get_summary_by_status(self) -> list[TaskSummaryByStatus]:
        """возвращает сводку по статусам"""

        return self.repository.get_summary_by_status()

    def update_task(self, task_id: UUID, payload: TaskUpdate) -> TaskRead:
        """частично обновляет задачу"""

        return self.repository.update_task(task_id=task_id, payload=payload)

    def update_task_for_user(
        self,
        task_id: UUID,
        payload: TaskUpdate,
        current_user: CurrentUser,
    ) -> TaskRead:
        """обновляет задачу если доступ разрешен"""

        self.get_task_for_user(task_id, current_user)
        return self.update_task(task_id=task_id, payload=payload)

    def assign_task(self, task_id: UUID, assignee_id: UUID) -> TaskRead:
        """назначает исполнителя задаче"""

        return self.repository.assign_task(
            task_id=task_id,
            assignee_id=assignee_id,
        )

    def assign_task_for_user(
        self,
        task_id: UUID,
        assignee_id: UUID,
        current_user: CurrentUser,
    ) -> TaskRead:
        """назначает исполнителя с учетом прав текущего пользователя"""

        self.get_task_for_user(task_id, current_user)
        ensure_assignment_allowed(assignee_id, current_user)
        return self.assign_task(task_id=task_id, assignee_id=assignee_id)

    def close_task(self, task_id: UUID, changed_by_user_id: UUID) -> TaskRead:
        """закрывает задачу"""

        return self.repository.close_task(
            task_id=task_id,
            changed_by_user_id=changed_by_user_id,
        )

    def close_task_for_user(
        self,
        task_id: UUID,
        current_user: CurrentUser,
    ) -> TaskRead:
        """закрывает задачу если доступ разрешен"""

        self.get_task_for_user(task_id, current_user)
        return self.close_task(task_id=task_id, changed_by_user_id=current_user.id)

    def archive_task(self, task_id: UUID) -> TaskRead:
        """архивирует задачу"""

        return self.repository.archive_task(task_id)

    def archive_task_for_user(
        self,
        task_id: UUID,
        current_user: CurrentUser,
    ) -> TaskRead:
        """архивирует задачу если доступ разрешен"""

        self.get_task_for_user(task_id, current_user)
        return self.archive_task(task_id)

    def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        changed_by_user_id: UUID,
    ) -> TaskRead:
        """меняет статус задачи"""

        return self.repository.update_task_status(
            task_id=task_id,
            status=status,
            changed_by_user_id=changed_by_user_id,
        )

    def update_task_status_for_user(
        self,
        task_id: UUID,
        status: TaskStatus,
        current_user: CurrentUser,
    ) -> TaskRead:
        """меняет статус задачи если доступ разрешен"""

        self.get_task_for_user(task_id, current_user)
        return self.update_task_status(
            task_id=task_id,
            status=status,
            changed_by_user_id=current_user.id,
        )
