from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.errors import AppError


def _build_error_payload(
    *, error_code: str, message: str, details: object | None = None
) -> dict[str, object]:
    """собирает единый формат ответа с ошибкой"""

    return {
        "error_code": error_code,
        "message": message,
        "details": details,
    }


def _normalize_context(context: dict[str, object]) -> dict[str, object]:
    """приводит context ошибки к json-совместимому виду"""

    normalized: dict[str, object] = {}
    for key, value in context.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            normalized[key] = value
            continue
        normalized[key] = str(value)
    return normalized


def _build_validation_details(
    exc: RequestValidationError,
) -> list[dict[str, object]]:
    """собирает машиночитаемые детали ошибок валидации"""

    details: list[dict[str, object]] = []
    for error in exc.errors():
        location = list(error["loc"])
        detail: dict[str, object] = {
            "location": location,
            "message": error["msg"],
            "error_type": error["type"],
        }
        if error.get("ctx"):
            detail["context"] = _normalize_context(error["ctx"])
        details.append(detail)
    return details


def register_exception_handlers(app: FastAPI) -> None:
    """регистрирует обработчики ошибок приложения"""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        """возвращает ответ для прикладных ошибок"""

        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_payload(
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """возвращает ответ для ошибок валидации запроса"""

        details = _build_validation_details(exc)
        has_json_error = any(
            detail["error_type"] == "json_invalid" for detail in details
        )
        if has_json_error:
            return JSONResponse(
                status_code=400,
                content=_build_error_payload(
                    error_code="malformed_json",
                    message="тело запроса содержит некорректный json",
                    details=details,
                ),
            )

        return JSONResponse(
            status_code=422,
            content=_build_error_payload(
                error_code="validation_error",
                message="запрос не прошел валидацию",
                details=details,
            ),
        )
