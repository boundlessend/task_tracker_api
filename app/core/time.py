from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def now_msk() -> datetime:
    """возвращает текущее московское время"""

    return datetime.now(MOSCOW_TZ)


def to_msk(dt: datetime | None) -> datetime | None:
    """приводит datetime к московскому часовому поясу"""

    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=MOSCOW_TZ)
    return dt.astimezone(MOSCOW_TZ)


def to_storage_datetime(dt: datetime | None) -> datetime | None:
    """готовит datetime к сохранению в базе"""

    normalized = to_msk(dt)
    if normalized is None:
        return None
    return normalized.replace(tzinfo=None)


def from_storage_datetime(dt: datetime | None) -> datetime | None:
    """восстанавливает московский часовой пояс после чтения из базы"""

    return to_msk(dt)
