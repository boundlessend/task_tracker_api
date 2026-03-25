import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.logging import configure_logging
from app.core.settings import AppEnv, get_settings

settings = get_settings()
configure_logging(settings.log_level.value)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "Запускаем шарманку | env=%s | port=%s | debug=%s",
        settings.app_env.value,
        settings.app_port,
        settings.debug,
    )
    yield
    logger.info("Останавливаем шарманку :(")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == AppEnv.DEV,
        log_level=settings.log_level.value.lower(),
    )
