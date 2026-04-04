from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text

from app.core.settings import get_settings

router = APIRouter(tags=["health"])


def ping_db(url: str | None) -> dict[str, bool | float | str | None]:
    started = time.perf_counter()

    if not url:
        return {
            "ok": False,
            "elapsed_ms": 0.0,
            "error": "database url is not set",
        }

    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()

        return {
            "ok": True,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": str(exc),
        }


@router.get("/health")
def healthcheck():
    """Возвращает статус приложения и проверку БД."""

    settings = get_settings()
    started = time.perf_counter()

    main_db = ping_db(settings.database_url)
    fake_db = ping_db(settings.fake_database_url)

    payload = {
        "status": "ok" if main_db["ok"] else "degraded",
        "service": settings.app_name,
        "env": settings.app_env.value,
        "debug": settings.debug,
        "time": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "database": main_db,
        "fake_database": fake_db,
    }

    return JSONResponse(
        content=payload,
        status_code=200 if main_db["ok"] else 503,
    )