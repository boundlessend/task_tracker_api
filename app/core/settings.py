import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class AppEnv(StrEnum):
    DEV = "dev"
    TEST = "test"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    app_name: str = "Task Tracker API"
    app_env: AppEnv = AppEnv.DEV
    app_host: str = Field(default="127.0.0.1", min_length=1)
    app_port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    secret_key: str = Field(default="misha_privet", min_length=8)

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        str_strip_whitespace=True,
        validate_default=True,
    )


def env_files_for(app_env: str | AppEnv) -> tuple[Path, ...]:
    try:
        return (BASE_DIR / f".env.{AppEnv(app_env).value}",)
    except ValueError as exc:
        allowed = ", ".join(env.value for env in AppEnv)
        raise RuntimeError(
            f"Неверный APP_ENV: {app_env!r}. Можно только такие значения: {allowed}."
        ) from exc


def _format_validation_error(exc: ValidationError) -> str:
    parts = [
        f"{(err.get('loc') or ['UNKNOWN'])[0].upper()}: {err.get('msg', 'Неверное значение')}"
        for err in exc.errors()
    ]
    return "Неверные настройки приложения. " + "; ".join(parts)


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings(
            _env_file=env_files_for(os.getenv("APP_ENV", AppEnv.DEV.value))
        )
    except ValidationError as exc:
        raise RuntimeError(_format_validation_error(exc)) from exc
