from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.settings import AppEnv, Settings, get_settings
from app.db.session import reset_db_state
from app.main import create_app

BASE_DIR = Path(__file__).resolve().parents[1]


def make_alembic_config() -> Config:
    """создает конфиг alembic для тестов"""

    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    return config


def migrate_sqlite_db(
    monkeypatch,
    tmp_path: Path,
    *,
    name: str,
) -> str:
    """поднимает отдельную sqlite базу и применяет миграции"""

    db_path = tmp_path / f"{name}.db"
    db_url = f"sqlite+pysqlite:///{db_path}"

    get_settings.cache_clear()
    reset_db_state()
    monkeypatch.setenv("DATABASE_URL", db_url)
    command.upgrade(make_alembic_config(), "head")
    get_settings.cache_clear()
    reset_db_state()

    return db_url


def create_user(client: TestClient, *, username: str, email: str) -> int:
    """создает пользователя и возвращает его id"""

    response = client.post(
        "/users",
        json={
            "username": username,
            "email": email,
            "full_name": username.title(),
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_app_uses_passed_settings_for_database(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """проверяет что create_app(settings=...) реально переключает базу данных"""

    first_db_url = migrate_sqlite_db(monkeypatch, tmp_path, name="first")
    second_db_url = migrate_sqlite_db(monkeypatch, tmp_path, name="second")

    first_app = create_app(
        Settings(
            app_env=AppEnv.TEST,
            debug=False,
            database_url=first_db_url,
        )
    )
    second_app = create_app(
        Settings(
            app_env=AppEnv.TEST,
            debug=False,
            database_url=second_db_url,
        )
    )

    first_client = TestClient(first_app)
    second_client = TestClient(second_app)

    author_id = create_user(
        first_client,
        username="maria",
        email="maria@example.com",
    )
    task_response = first_client.post(
        "/tasks",
        json={
            "title": "Изолированная задача",
            "description": "Должна остаться только в первой базе",
            "author_id": author_id,
            "status": "todo",
        },
    )
    assert task_response.status_code == 201

    first_tasks = first_client.get("/tasks")
    second_tasks = second_client.get("/tasks")

    assert first_tasks.status_code == 200
    assert second_tasks.status_code == 200
    assert first_tasks.json()["meta"]["total"] == 1
    assert second_tasks.json()["meta"]["total"] == 0
