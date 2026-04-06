from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.errors import AppError


def _build_error_payload(
    *, code: str, message: str, details: object | None = None
) -> dict[str, object]:
    """собирает единый формат ответа с ошибкой"""

    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """регистрирует обработчики ошибок приложения"""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        """возвращает ответ для бизнес-ошибок"""

        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_payload(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """возвращает ответ для ошибок валидации запроса"""

        details = [
            {
                "loc": list(error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_build_error_payload(
                code="validation_error",
                message="запрос не прошел валидацию",
                details=details,
            ),
        )
