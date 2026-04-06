from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions.errors import AppConfigurationError

BASE_DIR = Path(__file__).resolve().parents[2]


class AppEnv(str, Enum):
    """доступные окружения приложения"""

    DEV = "dev"
    TEST = "test"


class LogLevel(str, Enum):
    """доступные уровни логирования"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """описывает настройки приложения"""

    app_name: str = "Task Tracker API"
    app_env: AppEnv = AppEnv.DEV
    app_host: str = Field(default="127.0.0.1", min_length=1)
    app_port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    database_url: str = Field(min_length=1)
    database_echo: bool = False
    fake_database_url: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        str_strip_whitespace=True,
        validate_default=True,
    )


def env_files_for(app_env: str | AppEnv) -> tuple[Path, ...]:
    """возвращает env-файл для выбранного окружения"""

    try:
        return (BASE_DIR / f".env.{AppEnv(app_env).value}",)
    except ValueError as exc:
        allowed = ", ".join(env.value for env in AppEnv)
        raise AppConfigurationError(
            f"неверный APP_ENV: {app_env!r}. допустимые значения: {allowed}"
        ) from exc


def _format_validation_error(exc: ValidationError) -> str:
    """собирает читаемую ошибку валидации настроек"""

    parts = [
        (
            f"{(err.get('loc') or ['UNKNOWN'])[0].upper()}: "
            f"{err.get('msg', 'неверное значение')}"
        )
        for err in exc.errors()
    ]
    return "неверные настройки приложения: " + "; ".join(parts)


@lru_cache
def get_settings() -> Settings:
    """читает и кеширует настройки приложения"""

    try:
        return Settings(
            _env_file=env_files_for(os.getenv("APP_ENV", AppEnv.DEV.value))
        )
    except ValidationError as exc:
        raise AppConfigurationError(_format_validation_error(exc)) from exc
