from datetime import timedelta

from fastapi import Request, Response

from domains.user.domain.models.user import User
from infrastructure.auth.jwt import (
    AUTH_COOKIE_NAME,
    REMEMBER_ME_CLAIM,
    TOKEN_VERSION_CLAIM,
    create_access_token,
    set_auth_cookie,
    should_persist_auth_cookie,
)


def serialize_user(user: User) -> dict:
    return user.to_dict(exclude={'token_version'})


def issue_auth_cookie(
    http_response: Response,
    http_request: Request,
    user: User,
    *,
    remember_me: bool = False,
) -> None:
    access_token = create_access_token(
        data={
            'sub': str(user.id),
            TOKEN_VERSION_CLAIM: int(getattr(user, 'token_version', 0) or 0),
            REMEMBER_ME_CLAIM: bool(remember_me),
        },
        expires_delta=timedelta(days=30),
    )
    set_auth_cookie(http_response, access_token, http_request, persistent=remember_me)


def should_remember_current_session(http_request: Request) -> bool:
    return should_persist_auth_cookie(http_request.cookies.get(AUTH_COOKIE_NAME))
