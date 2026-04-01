from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import AppError, TaskNotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    """регистрирует обработчики ошибок приложения"""

    @app.exception_handler(TaskNotFoundError)
    async def handle_task_not_found(
        _: Request, exc: TaskNotFoundError
    ) -> JSONResponse:
        """возвращает ответ для отсутствующей задачи"""

        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        """возвращает ответ для бизнес-ошибок"""

        return JSONResponse(status_code=400, content={"detail": exc.message})
