from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.core.settings import Settings


def get_app_settings(request: Request) -> Settings:
    """возвращает настройки приложения из fastapi state"""

    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
