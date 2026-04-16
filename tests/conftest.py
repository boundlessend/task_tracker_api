import os
from pathlib import Path
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import (
    DDL,
    Integer,
    String,
    column,
    create_engine,
    func,
    select,
    table,
)
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.settings import get_settings
from app.db.session import reset_db_state

os.environ["APP_ENV"] = "test"

BASE_DIR = Path(__file__).resolve().parents[1]


def make_alembic_config() -> Config:
    """создает конфиг alembic для тестов"""

    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    return config


def reset_postgres_schema(database_url: str) -> None:
    """очищает public в тестовой postgres базе или создаёт базу если нет"""

    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/")

    maintenance_url = database_url.replace(f"/{db_name}", "/postgres", 1)
    pg_activity = table(
        "pg_stat_activity",
        column("pid", Integer),
        column("datname", String),
    )

    engine = create_engine(
        maintenance_url,
        future=True,
        isolation_level="AUTOCOMMIT",
    )
    with engine.connect() as connection:
        connection.execute(
            select(func.pg_terminate_backend(pg_activity.c.pid)).where(
                pg_activity.c.datname == db_name,
                pg_activity.c.pid != func.pg_backend_pid(),
            )
        )
        connection.execute(DDL(f'DROP DATABASE IF EXISTS "{db_name}"'))
        connection.execute(DDL(f'CREATE DATABASE "{db_name}"'))
    engine.dispose()

    engine = create_engine(
        database_url,
        future=True,
        isolation_level="AUTOCOMMIT",
    )
    with engine.connect() as connection:
        connection.execute(DropSchema("public", cascade=True, if_exists=True))
        connection.execute(CreateSchema("public"))
        current_user = connection.scalar(select(func.current_user()))
        connection.execute(
            DDL(f'GRANT ALL ON SCHEMA public TO "{current_user}"')
        )
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_settings_and_db_caches() -> None:
    """сбрасывает кеш настроек и базы между тестами"""

    get_settings.cache_clear()
    reset_db_state()
    yield
    get_settings.cache_clear()
    reset_db_state()


@pytest.fixture()
def migrated_sqlite_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    """поднимает чистую sqlite базу и применяет миграции"""

    db_path = tmp_path / "task_tracker_test.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    config = make_alembic_config()
    command.upgrade(config, "head")
    return db_url


@pytest.fixture()
def migrated_postgres_db(monkeypatch: pytest.MonkeyPatch) -> str:
    """поднимает чистую postgres базу и применяет миграции"""

    db_url = os.getenv("TEST_POSTGRES_DATABASE_URL")
    if not db_url:
        pytest.skip(
            "Не задан TEST_POSTGRES_DATABASE_URL "
            "для интеграционных тестов PostgreSQL"
        )

    monkeypatch.setenv("DATABASE_URL", db_url)
    reset_postgres_schema(db_url)

    config = make_alembic_config()
    command.upgrade(config, "head")

    yield db_url

    reset_postgres_schema(db_url)
