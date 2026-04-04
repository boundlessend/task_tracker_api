from __future__ import annotations

from app.repositories.tasks import TaskRepository
from app.schemas.tasks import (
    SortOrder,
    TaskCreate,
    TaskListResponse,
    TaskRead,
    TaskSortField,
    TaskStatus,
    TaskSummaryByStatus,
    TaskSummaryRead,
    TaskUpdate,
)


class TaskService:
    """содержит сценарии работы с задачами"""

    def __init__(self, repository: TaskRepository) -> None:
        """сохраняет репозиторий задач"""

        self.repository = repository

    def create_task(self, payload: TaskCreate) -> TaskRead:
        """создает задачу"""

        return self.repository.create_task(payload)

    def get_task(self, task_id: int) -> TaskRead:
        """возвращает задачу по идентификатору"""

        return self.repository.get_task(task_id)

    def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        author_id: int | None = None,
        assignee_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: TaskSortField = TaskSortField.UPDATED_AT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> TaskListResponse:
        """возвращает список задач"""

        return self.repository.list_tasks(
            status=status,
            author_id=author_id,
            assignee_id=assignee_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def search_tasks(self, query_text: str, limit: int = 20) -> list[TaskRead]:
        """ищет задачи"""

        return self.repository.search_tasks(query_text=query_text, limit=limit)

    def export_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        author_id: int | None = None,
        assignee_id: int | None = None,
        sort_by: TaskSortField = TaskSortField.UPDATED_AT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> list[TaskRead]:
        """возвращает задачи для выгрузки"""

        return self.repository.export_tasks(
            status=status,
            author_id=author_id,
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

    def update_task(self, task_id: int, payload: TaskUpdate) -> TaskRead:
        """частично обновляет задачу"""

        return self.repository.update_task(task_id=task_id, payload=payload)

    def assign_task(self, task_id: int, assignee_id: int) -> TaskRead:
        """назначает исполнителя задаче"""

        return self.repository.assign_task(
            task_id=task_id,
            assignee_id=assignee_id,
        )

    def archive_task(self, task_id: int) -> TaskRead:
        """архивирует задачу"""

        return self.repository.archive_task(task_id)

    def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        changed_by_user_id: int,
    ) -> TaskRead:
        """меняет статус задачи"""

        return self.repository.update_task_status(
            task_id=task_id,
            status=status,
            changed_by_user_id=changed_by_user_id,
        )
