from app.repositories.task_memory import InMemoryTaskRepository
from app.schemas.tasks import TaskRead


class TaskService:
    def __init__(self, repository: InMemoryTaskRepository) -> None:
        self.repository = repository

    def list_tasks(self) -> list[TaskRead]:
        return self.repository.list_tasks()


def get_task_service() -> TaskService:
    return TaskService(repository=InMemoryTaskRepository())
