from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.bootstrap import prepare_application_data
from app.core.logging import configure_logging
from app.core.settings import AppEnv, Settings, get_settings
from app.exceptions.handlers import register_exception_handlers
from app.routers.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """управляет жизненным циклом приложения"""

    settings: Settings = app.state.settings
    logger.info(
        "Запускаем приложение | env=%s | port=%s | debug=%s",
        settings.app_env.value,
        settings.app_port,
        settings.debug,
    )
    prepare_application_data(settings)
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
    app.state.settings = settings
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
