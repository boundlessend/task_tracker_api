import os
from collections.abc import Callable, Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
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
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.settings import get_settings
from app.db.session import get_engine, reset_db_state
from app.main import create_app
from app.repositories.tasks import TaskRepository
from app.services.tasks import TaskService

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
def reset_settings_and_db_caches() -> Iterator[None]:
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
def migrated_postgres_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
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


@pytest.fixture()
def client(migrated_sqlite_db: str) -> Iterator[TestClient]:
    """создает тестовый http-клиент приложения"""

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def db_session(migrated_sqlite_db: str) -> Iterator[Session]:
    """создает сессию базы данных для интеграционных тестов"""

    with Session(get_engine()) as session:
        yield session


@pytest.fixture()
def task_service(db_session: Session) -> TaskService:
    """создает сервис задач поверх тестовой сессии"""

    return TaskService(repository=TaskRepository(session=db_session))


@pytest.fixture()
def create_user(client: TestClient) -> Callable[..., str]:
    """создает пользователя через api и возвращает его id"""

    def _create_user(
        *, username: str, email: str, full_name: str | None = None
    ) -> str:
        response = client.post(
            "/users",
            json={
                "username": username,
                "email": email,
                "full_name": full_name or username.title(),
            },
        )
        assert response.status_code == 201
        return response.json()["id"]

    return _create_user


@pytest.fixture()
def create_task(client: TestClient) -> Callable[..., dict[str, object]]:
    """создает задачу через api и возвращает тело ответа"""

    def _create_task(
        *,
        owner_id: str,
        title: str = "Новая задача",
        description: str | None = None,
        assignee_id: str | None = None,
        status: str = "todo",
        due_date: str | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "title": title,
            "owner_id": owner_id,
            "status": status,
        }
        if description is not None:
            payload["description"] = description
        if assignee_id is not None:
            payload["assignee_id"] = assignee_id
        if due_date is not None:
            payload["due_date"] = due_date

        response = client.post("/tasks", json=payload)
        assert response.status_code == 201
        return response.json()

    return _create_task
