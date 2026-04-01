from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.router import api_router
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.settings import AppEnv, Settings, get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """управляет жизненным циклом приложения"""

    settings = get_settings()
    logger.info(
        "Запускаем приложение | env=%s | port=%s | debug=%s",
        settings.app_env.value,
        settings.app_port,
        settings.debug,
    )
    yield
    logger.info("Останавливаем приложение")


def create_app(settings: Settings | None = None) -> FastAPI:
    """создает экземпляр fastapi приложения"""

    settings = settings or get_settings()
    configure_logging(settings.log_level.value)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()


def run() -> None:
    """запускает uvicorn сервер"""

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == AppEnv.DEV,
        log_level=settings.log_level.value.lower(),
    )
