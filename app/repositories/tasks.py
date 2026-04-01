from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DataIntegrityError, TaskNotFoundError
from app.schemas.tasks import (
    SortOrder,
    TaskCreate,
    TaskRead,
    TaskSortField,
    TaskStatus,
    TaskSummaryByStatus,
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
    t.created_at,
    t.updated_at,
    COALESCE(comment_stats.comment_count, 0) AS comment_count
FROM tasks t
JOIN users author_user ON author_user.id = t.author_id
LEFT JOIN users assignee_user ON assignee_user.id = t.assignee_id
LEFT JOIN (
    SELECT task_id, COUNT(*) AS comment_count
    FROM comments
    GROUP BY task_id
) AS comment_stats ON comment_stats.task_id = t.id
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
    ) -> list[TaskRead]:
        """читает список задач с фильтрами и сортировкой"""

        where_clauses: list[str] = []
        params: dict[str, object] = {"limit": limit, "offset": offset}

        if status is not None:
            where_clauses.append("t.status = :status")
            params["status"] = status.value
        if author_id is not None:
            where_clauses.append("t.author_id = :author_id")
            params["author_id"] = author_id
        if assignee_id is not None:
            where_clauses.append("t.assignee_id = :assignee_id")
            params["assignee_id"] = assignee_id

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        order_sql = (
            f"{SORT_COLUMN_MAP[sort_by]} {sort_order.value.upper()}, t.id DESC"
        )
        order_sql += "\nLIMIT :limit\nOFFSET :offset"

        return self._fetch_many_tasks(
            where_sql=where_sql,
            order_sql=order_sql,
            params=params,
        )

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
