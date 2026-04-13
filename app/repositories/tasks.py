from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.errors import (
    DataIntegrityError,
    TaskConflictError,
    TaskNotFoundError,
)
from app.schemas.tasks import (
    SortOrder,
    TaskCreate,
    TaskListMeta,
    TaskListResponse,
    TaskRead,
    TaskSortField,
    TaskStatus,
    TaskSummaryByStatus,
    TaskSummaryRead,
    TaskUpdate,
)

TASK_SELECT_SQL = """
SELECT
    t.id,
    t.title,
    t.description,
    t.status,
    t.author_id,
    t.assignee_id,
    author_user.username AS author_username,
    assignee_user.username AS assignee_username,
    t.due_date,
    t.archived_at,
    t.created_at,
    t.updated_at,
    (
        SELECT COUNT(*)
        FROM comments comment_source
        WHERE comment_source.task_id = t.id
    ) AS comment_count
FROM tasks t
JOIN users author_user ON author_user.id = t.author_id
LEFT JOIN users assignee_user ON assignee_user.id = t.assignee_id
"""

SORT_COLUMN_MAP = {
    TaskSortField.CREATED_AT: "t.created_at",
    TaskSortField.UPDATED_AT: "t.updated_at",
}


class TaskRepository:
    """работает с задачами через явные sql-запросы"""

    def __init__(self, session: Session) -> None:
        """сохраняет сессию базы данных"""

        self.session = session

    def _fetch_one_task(
        self, where_sql: str, params: dict[str, object]
    ) -> TaskRead:
        """читает одну задачу по условию"""

        query = text(f"""{TASK_SELECT_SQL}\n{where_sql}""")
        row = self.session.execute(query, params).mappings().first()
        if row is None:
            raise TaskNotFoundError(
                f"Задача с id={params['task_id']} не найдена."
            )
        return TaskRead.model_validate(row)

    def _fetch_many_tasks(
        self,
        *,
        where_sql: str = "",
        order_sql: str,
        params: dict[str, object],
    ) -> list[TaskRead]:
        """читает список задач по условию и сортировке"""

        query = text(
            f"""
            {TASK_SELECT_SQL}
            {where_sql}
            ORDER BY {order_sql}
            """
        )
        rows = self.session.execute(query, params).mappings().all()
        return [TaskRead.model_validate(row) for row in rows]

    def _build_filters(
        self,
        *,
        status: TaskStatus | None = None,
        author_id: int | None = None,
        assignee_id: int | None = None,
    ) -> tuple[str, dict[str, object]]:
        """собирает where для фильтров списка задач"""

        where_clauses: list[str] = []
        params: dict[str, object] = {}

        if status is not None:
            where_clauses.append("t.status = :status")
            params["status"] = status.value
        if author_id is not None:
            where_clauses.append("t.author_id = :author_id")
            params["author_id"] = author_id
        if assignee_id is not None:
            where_clauses.append("t.assignee_id = :assignee_id")
            params["assignee_id"] = assignee_id

        if not where_clauses:
            return "", params
        return "WHERE " + " AND ".join(where_clauses), params

    def create_task(self, payload: TaskCreate) -> TaskRead:
        """создает задачу и пишет запись в историю"""

        insert_task = text(
            """
            INSERT INTO tasks (
                title,
                description,
                status,
                author_id,
                assignee_id,
                due_date
            )
            VALUES (
                :title,
                :description,
                :status,
                :author_id,
                :assignee_id,
                :due_date
            )
            RETURNING id
            """
        )
        insert_history = text(
            """
            INSERT INTO task_history (
                task_id,
                changed_by_user_id,
                action,
                new_status
            )
            VALUES (:task_id, :changed_by_user_id, 'created', :new_status)
            """
        )
        try:
            task_row = (
                self.session.execute(
                    insert_task,
                    {
                        **payload.model_dump(),
                        "status": payload.status.value,
                    },
                )
                .mappings()
                .one()
            )
            self.session.execute(
                insert_history,
                {
                    "task_id": task_row["id"],
                    "changed_by_user_id": payload.author_id,
                    "new_status": payload.status.value,
                },
            )
            task = self.get_task(task_row["id"])
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось создать задачу. "
                "Проверьте author_id, assignee_id и ограничения полей."
            ) from exc
        return task

    def get_task(self, task_id: int) -> TaskRead:
        """возвращает задачу по идентификатору"""

        return self._fetch_one_task(
            "WHERE t.id = :task_id",
            {"task_id": task_id},
        )

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
        """читает список задач с фильтрами и сортировкой"""

        where_sql, params = self._build_filters(
            status=status,
            author_id=author_id,
            assignee_id=assignee_id,
        )
        params.update({"limit": limit, "offset": offset})
        order_sql = (
            f"{SORT_COLUMN_MAP[sort_by]} {sort_order.value.upper()}, t.id DESC"
        )
        order_sql += "\nLIMIT :limit\nOFFSET :offset"

        items = self._fetch_many_tasks(
            where_sql=where_sql,
            order_sql=order_sql,
            params=params,
        )
        total = self.count_tasks(
            status=status,
            author_id=author_id,
            assignee_id=assignee_id,
        )
        return TaskListResponse(
            items=items,
            meta=TaskListMeta(
                limit=limit,
                offset=offset,
                count=len(items),
                total=total,
            ),
        )

    def export_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        author_id: int | None = None,
        assignee_id: int | None = None,
        sort_by: TaskSortField = TaskSortField.UPDATED_AT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> list[TaskRead]:
        """возвращает все задачи для выгрузки"""

        where_sql, params = self._build_filters(
            status=status,
            author_id=author_id,
            assignee_id=assignee_id,
        )
        order_sql = (
            f"{SORT_COLUMN_MAP[sort_by]} {sort_order.value.upper()}, t.id DESC"
        )
        return self._fetch_many_tasks(
            where_sql=where_sql,
            order_sql=order_sql,
            params=params,
        )

    def count_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        author_id: int | None = None,
        assignee_id: int | None = None,
    ) -> int:
        """считает количество задач по фильтрам"""

        where_sql, params = self._build_filters(
            status=status,
            author_id=author_id,
            assignee_id=assignee_id,
        )
        row = (
            self.session.execute(
                text(f"SELECT COUNT(*) AS total FROM tasks t {where_sql}"),
                params,
            )
            .mappings()
            .one()
        )
        return int(row["total"])

    def search_tasks(self, query_text: str, limit: int = 20) -> list[TaskRead]:
        """ищет задачи по заголовку и описанию"""

        return self._fetch_many_tasks(
            where_sql=(
                "WHERE lower(t.title) LIKE lower(:pattern) "
                "OR lower(COALESCE(t.description, '')) LIKE lower(:pattern)"
            ),
            order_sql="t.updated_at DESC, t.id DESC\nLIMIT :limit",
            params={"pattern": f"%{query_text}%", "limit": limit},
        )

    def get_summary(self) -> TaskSummaryRead:
        """возвращает сводку по задачам"""

        total_row = (
            self.session.execute(text("SELECT COUNT(*) AS total FROM tasks"))
            .mappings()
            .one()
        )
        archived_row = (
            self.session.execute(
                text(
                    "SELECT COUNT(*) AS archived FROM tasks "
                    "WHERE archived_at IS NOT NULL"
                )
            )
            .mappings()
            .one()
        )
        return TaskSummaryRead(
            total=int(total_row["total"]),
            archived=int(archived_row["archived"]),
            by_status=self.get_summary_by_status(),
        )

    def get_summary_by_status(self) -> list[TaskSummaryByStatus]:
        """считает сводку задач по статусам"""

        query = text(
            """
            SELECT status, COUNT(*) AS task_count
            FROM tasks
            GROUP BY status
            ORDER BY status ASC
            """
        )
        rows = self.session.execute(query).mappings().all()
        return [TaskSummaryByStatus.model_validate(row) for row in rows]

    def update_task(self, task_id: int, payload: TaskUpdate) -> TaskRead:
        """частично обновляет задачу"""

        self.get_task(task_id)
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self.get_task(task_id)

        set_clauses = []
        params: dict[str, object] = {"task_id": task_id}
        for field_name, value in updates.items():
            set_clauses.append(f"{field_name} = :{field_name}")
            params[field_name] = value
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")

        try:
            self.session.execute(
                text(
                    """
                    UPDATE tasks
                    SET {set_clause}
                    WHERE id = :task_id
                    """.format(
                        set_clause=", ".join(set_clauses)
                    )
                ),
                params,
            )
            task = self.get_task(task_id)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось обновить задачу. Проверьте ограничения полей."
            ) from exc
        return task

    def assign_task(self, task_id: int, assignee_id: int) -> TaskRead:
        """назначает исполнителя задаче и переводит todo в in_progress"""

        existing = (
            self.session.execute(
                text(
                    """
                    SELECT assignee_id, status
                    FROM tasks
                    WHERE id = :task_id
                    """
                ),
                {"task_id": task_id},
            )
            .mappings()
            .first()
        )
        if existing is None:
            raise TaskNotFoundError(f"Задача с id={task_id} не найдена.")

        new_status = (
            TaskStatus.IN_PROGRESS.value
            if existing["status"] == TaskStatus.TODO.value
            else existing["status"]
        )
        if (
            existing["assignee_id"] == assignee_id
            and existing["status"] == new_status
        ):
            return self.get_task(task_id)

        try:
            self.session.execute(
                text(
                    """
                    UPDATE tasks
                    SET assignee_id = :assignee_id,
                        status = :status,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :task_id
                    """
                ),
                {
                    "task_id": task_id,
                    "assignee_id": assignee_id,
                    "status": new_status,
                },
            )
            if existing["status"] != new_status:
                self.session.execute(
                    text(
                        """
                        INSERT INTO task_history (
                            task_id,
                            changed_by_user_id,
                            action,
                            old_status,
                            new_status
                        )
                        VALUES (
                            :task_id,
                            :changed_by_user_id,
                            'status_changed',
                            :old_status,
                            :new_status
                        )
                        """
                    ),
                    {
                        "task_id": task_id,
                        "changed_by_user_id": assignee_id,
                        "old_status": existing["status"],
                        "new_status": new_status,
                    },
                )
            task = self.get_task(task_id)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось назначить исполнителя. Проверьте assignee_id."
            ) from exc
        return task

    def close_task(self, task_id: int, changed_by_user_id: int) -> TaskRead:
        """закрывает задачу переводом в done"""

        existing = (
            self.session.execute(
                text("SELECT status FROM tasks WHERE id = :task_id"),
                {"task_id": task_id},
            )
            .mappings()
            .first()
        )
        if existing is None:
            raise TaskNotFoundError(f"Задача с id={task_id} не найдена.")
        if existing["status"] == TaskStatus.DONE.value:
            raise TaskConflictError("Задача уже закрыта.")

        try:
            self.session.execute(
                text(
                    """
                    UPDATE tasks
                    SET status = :status,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :task_id
                    """
                ),
                {"task_id": task_id, "status": TaskStatus.DONE.value},
            )
            self.session.execute(
                text(
                    """
                    INSERT INTO task_history (
                        task_id,
                        changed_by_user_id,
                        action,
                        old_status,
                        new_status
                    )
                    VALUES (
                        :task_id,
                        :changed_by_user_id,
                        'status_changed',
                        :old_status,
                        :new_status
                    )
                    """
                ),
                {
                    "task_id": task_id,
                    "changed_by_user_id": changed_by_user_id,
                    "old_status": existing["status"],
                    "new_status": TaskStatus.DONE.value,
                },
            )
            task = self.get_task(task_id)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось закрыть задачу. Проверьте changed_by_user_id."
            ) from exc
        return task

    def archive_task(self, task_id: int) -> TaskRead:
        """архивирует задачу"""

        existing = (
            self.session.execute(
                text("SELECT archived_at FROM tasks WHERE id = :task_id"),
                {"task_id": task_id},
            )
            .mappings()
            .first()
        )
        if existing is None:
            raise TaskNotFoundError(f"Задача с id={task_id} не найдена.")
        if existing["archived_at"] is not None:
            raise TaskConflictError("Задача уже находится в архиве.")

        self.session.execute(
            text(
                """
                UPDATE tasks
                SET archived_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :task_id
                """
            ),
            {"task_id": task_id},
        )
        task = self.get_task(task_id)
        self.session.commit()
        return task

    def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        changed_by_user_id: int,
    ) -> TaskRead:
        """обновляет статус задачи и пишет запись в историю"""

        existing = (
            self.session.execute(
                text("SELECT status FROM tasks WHERE id = :task_id"),
                {"task_id": task_id},
            )
            .mappings()
            .first()
        )
        if existing is None:
            raise TaskNotFoundError(f"Задача с id={task_id} не найдена.")

        old_status = existing["status"]
        try:
            self.session.execute(
                text(
                    """
                    UPDATE tasks
                    SET status = :status,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :task_id
                    """
                ),
                {"task_id": task_id, "status": status.value},
            )
            self.session.execute(
                text(
                    """
                    INSERT INTO task_history (
                        task_id,
                        changed_by_user_id,
                        action,
                        old_status,
                        new_status
                    )
                    VALUES (
                        :task_id,
                        :changed_by_user_id,
                        'status_changed',
                        :old_status,
                        :new_status
                    )
                    """
                ),
                {
                    "task_id": task_id,
                    "changed_by_user_id": changed_by_user_id,
                    "old_status": old_status,
                    "new_status": status.value,
                },
            )
            task = self.get_task(task_id)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DataIntegrityError(
                "Не удалось изменить статус задачи. Проверьте changed_by_user_id."
            ) from exc
        return task
