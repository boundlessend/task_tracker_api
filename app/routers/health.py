from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import create_engine, select

from app.core.settings import Settings
from app.dependencies.settings import SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(settings: SettingsDep) -> dict[str, object]:
    """проверяет доступность базы данных и приложения"""

    database_ok = _probe_database(settings)
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env.value,
        "debug": settings.debug,
        "database": {"ok": database_ok},
    }


def _probe_database(settings: Settings) -> bool:
    """проверяет соединение с базой данных"""

    engine = create_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=True,
    )
    try:
        with engine.connect() as connection:
            connection.execute(select(1))
    finally:
        engine.dispose()
    return True
