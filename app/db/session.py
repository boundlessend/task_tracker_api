from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings


def _is_sqlite(url: str) -> bool:
    """проверяет что используется sqlite"""

    return url.startswith("sqlite")


@lru_cache
def get_engine() -> Engine:
    """создает и кеширует движок базы данных"""

    settings = get_settings()
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
        def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            """включает внешние ключи в sqlite"""

            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """создает фабрику сессий sql alchemy"""

    return sessionmaker(
        bind=get_engine(), autoflush=False, autocommit=False, future=True
    )


def get_db_session() -> Session:
    """возвращает сессию базы данных для запроса"""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def reset_db_state() -> None:
    """сбрасывает кеш движка и фабрики сессий"""

    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
