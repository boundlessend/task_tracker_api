from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.time import from_storage_datetime, now_msk, to_storage_datetime
from app.db.models import Comment, Task, TaskHistory, User
from app.exceptions.errors import (
    DataIntegrityError,
    TaskAlreadyClosedError,
    TaskConflictError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.schemas.comments import CommentRead
from app.schemas.task_history import TaskHistoryRead
from app.schemas.tasks import (
    SortOrder,
    TaskCreate,
    TaskListItemRead,
    TaskListMeta,
    TaskListResponse,
    TaskRead,
    TaskSortField,
    TaskStatus,
    TaskSummaryByStatus,
    TaskSummaryRead,
    TaskUpdate,
)


class TaskRepository:
    """работает с задачами через sqlalchemy"""

    def __init__(self, session: Session) -> None:
        """сохраняет сессию базы данных"""

        self.session = session

    @staticmethod
    def _build_task_not_found_error(task_id: UUID) -> TaskNotFoundError:
        """собирает доменную ошибку отсутствующей задачи"""

        return TaskNotFoundError(
            f"Задача с id={task_id} не найдена.",
            details={"task_id": str(task_id)},
        )

    def _ensure_user_exists(self, user_id: UUID, field_name: str) -> None:
        """проверяет что пользователь существует"""

        if self.session.get(User, user_id) is None:
            raise UserNotFoundError(
                (
                    f"Пользователь для поля {field_name} "
                    f"с id={user_id} не найден."
                ),
                details={"field": field_name, "user_id": str(user_id)},
            )

    @staticmethod
    def _map_comment(comment: Comment) -> CommentRead:
        """преобразует orm-модель комментария в схему"""

        return CommentRead.model_validate(
            {
                "id": comment.id,
                "task_id": comment.task_id,
                "author_id": comment.author_id,
                "text": comment.text,
                "created_at": from_storage_datetime(comment.created_at),
                "updated_at": from_storage_datetime(comment.updated_at),
                "author": {
                    "id": comment.author.id,
                    "username": comment.author.username,
                    "full_name": comment.author.full_name,
                },
            }
        )

    @staticmethod
    def _map_history_entry(entry: TaskHistory) -> TaskHistoryRead:
        """преобразует orm-модель истории в схему"""

        return TaskHistoryRead.model_validate(
            {
                "id": entry.id,
                "task_id": entry.task_id,
                "changed_by_user_id": entry.changed_by_user_id,
                "action": entry.action,
                "old_status": entry.old_status,
                "new_status": entry.new_status,
                "comment_text": entry.comment_text,
                "created_at": from_storage_datetime(entry.created_at),
                "changed_by": {
                    "id": entry.changed_by.id,
                    "username": entry.changed_by.username,
                    "full_name": entry.changed_by.full_name,
                },
            }
        )

    @staticmethod
    def _map_task_list_item(
        task: Task,
        comment_count: int,
    ) -> TaskListItemRead:
        """преобразует orm-модель задачи в схему списка"""

        return TaskListItemRead.model_validate(
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "owner_id": task.owner_id,
                "assignee_id": task.assignee_id,
                "due_date": from_storage_datetime(task.due_date),
                "archived_at": from_storage_datetime(task.archived_at),
                "created_at": from_storage_datetime(task.created_at),
                "updated_at": from_storage_datetime(task.updated_at),
                "closed_at": from_storage_datetime(task.closed_at),
                "comment_count": comment_count,
                "owner": {
                    "id": task.owner.id,
                    "username": task.owner.username,
                    "full_name": task.owner.full_name,
                },
                "assignee": (
                    {
                        "id": task.assignee.id,
                        "username": task.assignee.username,
                        "full_name": task.assignee.full_name,
                    }
                    if task.assignee is not None
                    else None
                ),
            }
        )

    def _map_task_read(self, task: Task) -> TaskRead:
        """преобразует orm-модель задачи в детальную схему"""

        list_item = self._map_task_list_item(task, len(task.comments))
        return TaskRead.model_validate(
            {
                **list_item.model_dump(),
                "comments": [
                    self._map_comment(comment).model_dump()
                    for comment in task.comments
                ],
                "history": [
                    self._map_history_entry(entry).model_dump()
                    for entry in task.history
                ],
            }
        )

    @staticmethod
    def _sort_expression(sort_by: TaskSortField, sort_order: SortOrder):
        """строит выражение сортировки"""

        column = getattr(Task, sort_by.value)
        if sort_order == SortOrder.ASC:
            return column.asc(), Task.id.asc()
        return column.desc(), Task.id.desc()

    @staticmethod
    def _build_filters(
        *,
        status: TaskStatus | None = None,
        owner_id: UUID | None = None,
        assignee_id: UUID | None = None,
    ) -> list[object]:
        """собирает фильтры списка задач"""

        filters: list[object] = []
        if status is not None:
            filters.append(Task.status == status.value)
        if owner_id is not None:
            filters.append(Task.owner_id == owner_id)
        if assignee_id is not None:
            filters.append(Task.assignee_id == assignee_id)
        return filters

    def _task_list_query(
        self,
        filters: list[object],
    ) -> Select[tuple[Task, int]]:
        """строит базовый запрос списка задач"""

        comment_count_subquery = (
            select(
                Comment.task_id.label("task_id"),
                func.count(Comment.id).label("comment_count"),
            )
            .group_by(Comment.task_id)
            .subquery()
        )
        return (
            select(
                Task,
                func.coalesce(comment_count_subquery.c.comment_count, 0),
            )
            .outerjoin(
                comment_count_subquery,
                comment_count_subquery.c.task_id == Task.id,
            )
            .options(selectinload(Task.owner), selectinload(Task.assignee))
            .where(*filters)
        )

    def _get_task_model(self, task_id: UUID) -> Task:
        """возвращает orm-модель задачи с зависимостями"""

        task = self.session.scalar(
            select(Task)
            .where(Task.id == task_id)
            .options(
                joinedload(Task.owner),
                joinedload(Task.assignee),
                selectinload(Task.comments).joinedload(Comment.author),
                selectinload(Task.history).joinedload(TaskHistory.changed_by),
            )
        )
        if task is None:
            raise self._build_task_not_found_error(task_id)
        return task

    def create_task(self, payload: TaskCreate) -> TaskRead:
        """создает задачу и запись в истории"""

        self._ensure_user_exists(payload.owner_id, "owner_id")
        if payload.assignee_id is not None:
            self._ensure_user_exists(payload.assignee_id, "assignee_id")

        task = Task(
            title=payload.title,
            description=payload.description,
            owner_id=payload.owner_id,
            assignee_id=payload.assignee_id,
            status=payload.status.value,
            due_date=to_storage_datetime(payload.due_date),
            closed_at=(
                to_storage_datetime(now_msk())
                if payload.status == TaskStatus.DONE
                else None
            ),
        )
        history_entry = TaskHistory(
            task=task,
            changed_by_user_id=payload.owner_id,
            action="created",
            new_status=payload.status.value,
        )
        self.session.add(task)
        self.session.add(history_entry)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось создать задачу. "
                "Проверьте owner_id, assignee_id и ограничения полей.",
                details={"entity": "task", "operation": "create"},
            ) from exc
        return self.get_task(task.id)

    def get_task(self, task_id: UUID) -> TaskRead:
        """возвращает задачу по идентификатору"""

        return self._map_task_read(self._get_task_model(task_id))

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
        """возвращает список задач с пагинацией"""

        filters = self._build_filters(
            status=status,
            owner_id=owner_id,
            assignee_id=assignee_id,
        )
        total = self.session.scalar(
            select(func.count()).select_from(Task).where(*filters)
        )
        rows = self.session.execute(
            self._task_list_query(filters)
            .order_by(*self._sort_expression(sort_by, sort_order))
            .offset(offset)
            .limit(limit)
        ).all()
        items = [
            self._map_task_list_item(task, int(comment_count))
            for task, comment_count in rows
        ]
        return TaskListResponse(
            items=items,
            meta=TaskListMeta(
                limit=limit,
                offset=offset,
                count=len(items),
                total=int(total or 0),
            ),
        )

    def export_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        owner_id: UUID | None = None,
        assignee_id: UUID | None = None,
        sort_by: TaskSortField = TaskSortField.UPDATED_AT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> list[TaskListItemRead]:
        """возвращает все задачи для выгрузки"""

        filters = self._build_filters(
            status=status,
            owner_id=owner_id,
            assignee_id=assignee_id,
        )
        rows = self.session.execute(
            self._task_list_query(filters).order_by(
                *self._sort_expression(sort_by, sort_order)
            )
        ).all()
        return [
            self._map_task_list_item(task, int(comment_count))
            for task, comment_count in rows
        ]

    def search_tasks(
        self,
        query_text: str,
        limit: int = 20,
    ) -> list[TaskListItemRead]:
        """ищет задачи по заголовку и описанию"""

        pattern = f"%{query_text.lower()}%"
        rows = self.session.execute(
            self._task_list_query(
                [
                    or_(
                        func.lower(Task.title).like(pattern),
                        func.lower(func.coalesce(Task.description, "")).like(
                            pattern
                        ),
                    )
                ]
            )
            .order_by(Task.updated_at.desc(), Task.id.desc())
            .limit(limit)
        ).all()
        return [
            self._map_task_list_item(task, int(comment_count))
            for task, comment_count in rows
        ]

    def get_summary(self) -> TaskSummaryRead:
        """возвращает сводку по задачам"""

        total = self.session.scalar(select(func.count()).select_from(Task))
        archived = self.session.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.archived_at.is_not(None))
        )
        return TaskSummaryRead(
            total=int(total or 0),
            archived=int(archived or 0),
            by_status=self.get_summary_by_status(),
        )

    def get_summary_by_status(self) -> list[TaskSummaryByStatus]:
        """считает сводку задач по статусам"""

        rows = self.session.execute(
            select(Task.status, func.count(Task.id))
            .group_by(Task.status)
            .order_by(Task.status.asc())
        ).all()
        return [
            TaskSummaryByStatus(status=status, task_count=int(task_count))
            for status, task_count in rows
        ]

    def update_task(self, task_id: UUID, payload: TaskUpdate) -> TaskRead:
        """частично обновляет задачу"""

        task = self._get_task_model(task_id)
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self._map_task_read(task)

        if "title" in updates:
            task.title = updates["title"]
        if "description" in updates:
            task.description = updates["description"]
        if "due_date" in updates:
            task.due_date = to_storage_datetime(updates["due_date"])
        task.updated_at = to_storage_datetime(now_msk())

        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось обновить задачу. " "Проверьте ограничения полей.",
                details={
                    "entity": "task",
                    "operation": "update",
                    "task_id": str(task_id),
                },
            ) from exc
        return self.get_task(task_id)

    def assign_task(self, task_id: UUID, assignee_id: UUID) -> TaskRead:
        """назначает исполнителя задаче и переводит todo в in_progress"""

        self._ensure_user_exists(assignee_id, "assignee_id")
        task = self._get_task_model(task_id)

        new_status = (
            TaskStatus.IN_PROGRESS.value
            if task.status == TaskStatus.TODO.value
            else task.status
        )
        if task.assignee_id == assignee_id and task.status == new_status:
            return self._map_task_read(task)

        old_status = task.status
        task.assignee_id = assignee_id
        task.status = new_status
        task.updated_at = to_storage_datetime(now_msk())

        if old_status != new_status:
            self.session.add(
                TaskHistory(
                    task_id=task.id,
                    changed_by_user_id=assignee_id,
                    action="status_changed",
                    old_status=old_status,
                    new_status=new_status,
                )
            )

        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось назначить исполнителя. " "Проверьте assignee_id.",
                details={
                    "entity": "task",
                    "operation": "assign",
                    "task_id": str(task_id),
                },
            ) from exc
        return self.get_task(task_id)

    def close_task(self, task_id: UUID, changed_by_user_id: UUID) -> TaskRead:
        """закрывает задачу переводом в done"""

        self._ensure_user_exists(changed_by_user_id, "changed_by_user_id")
        task = self._get_task_model(task_id)
        if task.status == TaskStatus.DONE.value:
            raise TaskAlreadyClosedError(
                "Задача уже закрыта.",
                details={
                    "task_id": str(task_id),
                    "status": TaskStatus.DONE.value,
                },
            )

        old_status = task.status
        closed_at = to_storage_datetime(now_msk())
        task.status = TaskStatus.DONE.value
        task.closed_at = closed_at
        task.updated_at = closed_at
        self.session.add(
            TaskHistory(
                task_id=task.id,
                changed_by_user_id=changed_by_user_id,
                action="status_changed",
                old_status=old_status,
                new_status=TaskStatus.DONE.value,
            )
        )

        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось закрыть задачу. Проверьте changed_by_user_id.",
                details={
                    "entity": "task",
                    "operation": "close",
                    "task_id": str(task_id),
                },
            ) from exc
        return self.get_task(task_id)

    def archive_task(self, task_id: UUID) -> TaskRead:
        """архивирует задачу"""

        task = self._get_task_model(task_id)
        if task.archived_at is not None:
            raise TaskConflictError(
                "Задача уже находится в архиве.",
                details={"task_id": str(task_id), "status": "archived"},
            )

        archived_at = to_storage_datetime(now_msk())
        task.archived_at = archived_at
        task.updated_at = archived_at
        self.session.commit()
        return self.get_task(task_id)

    def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        changed_by_user_id: UUID,
    ) -> TaskRead:
        """обновляет статус задачи и пишет запись в историю"""

        self._ensure_user_exists(changed_by_user_id, "changed_by_user_id")
        task = self._get_task_model(task_id)

        old_status = task.status
        task.status = status.value
        current_time = to_storage_datetime(now_msk())
        if status == TaskStatus.DONE:
            task.closed_at = task.closed_at or current_time
        else:
            task.closed_at = None
        task.updated_at = current_time
        self.session.add(
            TaskHistory(
                task_id=task.id,
                changed_by_user_id=changed_by_user_id,
                action="status_changed",
                old_status=old_status,
                new_status=status.value,
            )
        )

        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось изменить статус задачи. "
                "Проверьте changed_by_user_id.",
                details={
                    "entity": "task",
                    "operation": "update_status",
                    "task_id": str(task_id),
                },
            ) from exc
        return self.get_task(task_id)
