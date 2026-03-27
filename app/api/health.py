from __future__ import annotations

from fastapi import APIRouter

from app.core.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env.value,
        "debug": settings.debug,
    }
