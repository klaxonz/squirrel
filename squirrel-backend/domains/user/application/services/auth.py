"""Authentication service - handles JWT validation and user lookup"""

import logging

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt

import domains.user.application.services.service as user_service
from domains.user.domain.models.user import User
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from infrastructure.auth.jwt import (
    ALGORITHM,
    AUTH_COOKIE_NAME,
    TOKEN_VERSION_CLAIM,
    _get_secret_key,
)

logger = logging.getLogger(__name__)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )


async def get_current_user(
    token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> CurrentUserDto:
    """Validate the auth cookie and return the resolved current user.

    Returns a ``CurrentUserDto`` -- a small, serialisation-safe projection of
    the ORM ``User`` row -- so routes cannot accidentally leak sensitive ORM
    columns (e.g. ``token_version``) or relationships to the HTTP boundary.
    """
    _, user = validate_auth_token(token)
    return CurrentUserDto.model_validate(user)


def validate_auth_token(token: str | None) -> tuple[dict, User]:
    credentials_exception = _credentials_exception()

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
        subject = payload.get('sub')
        if subject is None:
            raise credentials_exception

        user_id = int(subject)
        user = user_service.get_user_by_id(user_id)
        if user is None:
            raise credentials_exception

        token_version = int(payload.get(TOKEN_VERSION_CLAIM, 0))
        current_version = int(getattr(user, 'token_version', 0) or 0)
        if token_version != current_version:
            raise credentials_exception

        return payload, user
    except (JWTError, TypeError, ValueError) as exc:
        raise credentials_exception from exc
