from pathlib import Path

import pytest

from app.core.errors import AppConfigurationError
from app.core.settings import AppEnv, LogLevel, get_settings


def write_env_file(
    path: Path,
    *,
    app_env: str = "dev",
    app_port: str = "8000",
    debug: str = "true",
    log_level: str = "INFO",
    database_url: str = "sqlite+pysqlite:///./settings-test.db",
) -> None:
    """записывает временный env-файл для теста"""

    path.write_text(
        "\n".join(
            [
                f"APP_ENV={app_env}",
                "APP_HOST=127.0.0.1",
                f"APP_PORT={app_port}",
                f"DEBUG={debug}",
                f"LOG_LEVEL={log_level}",
                f"DATABASE_URL={database_url}",
                "DATABASE_ECHO=false",
            ]
        ),
        encoding="utf-8",
    )


def test_invalid_app_port_raises_app_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """проверяет валидацию порта приложения"""

    env_file = tmp_path / ".env.dev"
    write_env_file(env_file, app_port="70000")

    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setattr(
        "app.core.settings.env_files_for", lambda app_env: (env_file,)
    )

    with pytest.raises(AppConfigurationError, match="APP_PORT"):
        get_settings()


def test_invalid_debug_raises_app_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """проверяет валидацию debug"""

    env_file = tmp_path / ".env.dev"
    write_env_file(env_file, debug="not-a-bool")

    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setattr(
        "app.core.settings.env_files_for", lambda app_env: (env_file,)
    )

    with pytest.raises(AppConfigurationError, match="DEBUG"):
        get_settings()


def test_invalid_log_level_raises_app_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """проверяет валидацию уровня логирования"""

    env_file = tmp_path / ".env.dev"
    write_env_file(env_file, log_level="LOUD")

    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setattr(
        "app.core.settings.env_files_for", lambda app_env: (env_file,)
    )

    with pytest.raises(AppConfigurationError, match="LOG_LEVEL"):
        get_settings()


def test_app_env_switches_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """проверяет переключение env-профиля"""

    dev_file = tmp_path / ".env.dev"
    test_file = tmp_path / ".env.test"

    write_env_file(
        dev_file,
        app_env="dev",
        app_port="8000",
        debug="true",
        log_level="INFO",
    )
    write_env_file(
        test_file,
        app_env="test",
        app_port="9000",
        debug="false",
        log_level="WARNING",
    )

    monkeypatch.setattr(
        "app.core.settings.env_files_for",
        lambda app_env: (tmp_path / f".env.{app_env}",),
    )

    monkeypatch.setenv("APP_ENV", "dev")
    dev_settings = get_settings()
    assert dev_settings.app_env is AppEnv.DEV
    assert dev_settings.app_port == 8000
    assert dev_settings.debug is True
    assert dev_settings.log_level is LogLevel.INFO

    get_settings.cache_clear()

    monkeypatch.setenv("APP_ENV", "test")
    test_settings = get_settings()
    assert test_settings.app_env is AppEnv.TEST
    assert test_settings.app_port == 9000
    assert test_settings.debug is False
    assert test_settings.log_level is LogLevel.WARNING
