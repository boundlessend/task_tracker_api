from app.schemas.tasks import TaskRead

_TASKS: list[TaskRead] = [
    TaskRead(id=1, title="Разобрать flow запроса", done=True),
    TaskRead(id=2, title="Вынести tasks в сервис", done=False),
]


class InMemoryTaskRepository:
    def list_tasks(self) -> list[TaskRead]:
        return list(_TASKS)
