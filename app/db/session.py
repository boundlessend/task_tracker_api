from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import Settings, get_settings

_ENGINE_CACHE: dict[tuple[str, bool], Engine] = {}
_SESSION_FACTORY_CACHE: dict[tuple[str, bool], sessionmaker[Session]] = {}


def _is_sqlite(url: str) -> bool:
    """проверяет что используется sqlite"""

    return url.startswith("sqlite")


def _cache_key(settings: Settings) -> tuple[str, bool]:
    """формирует ключ кеша для ресурсов базы данных"""

    return (settings.database_url, settings.database_echo)


def get_engine(settings: Settings | None = None) -> Engine:
    """возвращает движок базы данных для переданных настроек"""

    settings = settings or get_settings()
    key = _cache_key(settings)

    if key not in _ENGINE_CACHE:
        connect_args: dict[str, object] = {}
        if _is_sqlite(settings.database_url):
            connect_args["check_same_thread"] = False

        engine = create_engine(
            settings.database_url,
            future=True,
            echo=settings.database_echo,
            pool_pre_ping=not _is_sqlite(settings.database_url),
            connect_args=connect_args,
        )

        if _is_sqlite(settings.database_url):

            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(
                dbapi_connection, _connection_record
            ) -> None:
                """включает внешние ключи в sqlite"""

                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        _ENGINE_CACHE[key] = engine

    return _ENGINE_CACHE[key]


def get_session_factory(
    settings: Settings | None = None,
) -> sessionmaker[Session]:
    """возвращает фабрику сессий для переданных настроек"""

    settings = settings or get_settings()
    key = _cache_key(settings)

    if key not in _SESSION_FACTORY_CACHE:
        _SESSION_FACTORY_CACHE[key] = sessionmaker(
            bind=get_engine(settings),
            autoflush=False,
            autocommit=False,
            future=True,
        )

    return _SESSION_FACTORY_CACHE[key]


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """возвращает сессию базы данных для запроса"""

    settings: Settings = request.app.state.settings
    session = get_session_factory(settings)()
    try:
        yield session
    finally:
        session.close()


def reset_db_state() -> None:
    """сбрасывает кеш движка и фабрики сессий"""

    for engine in _ENGINE_CACHE.values():
        engine.dispose()

    _SESSION_FACTORY_CACHE.clear()
    _ENGINE_CACHE.clear()
