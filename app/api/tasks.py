from fastapi import APIRouter, Depends

from app.schemas.tasks import TaskRead
from app.services.tasks import TaskService, get_task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(
    service: TaskService = Depends(get_task_service),
) -> list[TaskRead]:
    return service.list_tasks()
