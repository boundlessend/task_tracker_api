from __future__ import annotations

from typing import Annotated

from fastapi import Header

from app.dependencies.services import UserServiceDep
from app.exceptions.errors import AuthenticationError
from app.schemas.users import CurrentUser
from app.services.users import STUB_TOKEN_PREFIX

STUB_USER_HEADER = "X-Auth-User"


def _extract_username_from_token(token: str) -> str:
    """извлекает username из учебного токена"""

    if not token.startswith(STUB_TOKEN_PREFIX):
        raise AuthenticationError(
            "неподдерживаемый формат токена",
            details={"token_type": "stub"},
        )
    username = token.removeprefix(STUB_TOKEN_PREFIX).strip()
    if not username:
        raise AuthenticationError("токен не содержит username")
    return username


def get_current_user(
    service: UserServiceDep,
    authorization: Annotated[str | None, Header()] = None,
    x_auth_user: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """возвращает текущего пользователя из auth-заголовков"""

    username: str | None = None

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthenticationError(
                "ожидался заголовок authorization в формате bearer <token>"
            )
        username = _extract_username_from_token(token)
    elif x_auth_user:
        username = x_auth_user.strip()

    if not username:
        raise AuthenticationError(
            "не передан заголовок аутентификации",
            details={"headers": ["authorization", STUB_USER_HEADER.lower()]},
        )

    return service.get_current_user_by_username(username)


CurrentUserDep = CurrentUser
