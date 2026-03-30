import os

import pytest

from app.core.settings import get_settings

os.environ["APP_ENV"] = "test"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
