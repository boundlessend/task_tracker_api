import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.core.settings import get_settings
from app.db.session import reset_db_state

os.environ["APP_ENV"] = "test"

BASE_DIR = Path(__file__).resolve().parents[1]


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

    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    command.upgrade(config, "head")
    return db_url
