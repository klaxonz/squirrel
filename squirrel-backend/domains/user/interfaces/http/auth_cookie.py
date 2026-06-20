from datetime import timedelta

from fastapi import Request, Response

from domains.user.domain.models.user import User
from domains.user.interfaces.dto.user_responses import UserResponse
from infrastructure.auth.jwt import (
    AUTH_COOKIE_NAME,
    REMEMBER_ME_CLAIM,
    TOKEN_VERSION_CLAIM,
    create_access_token,
    set_auth_cookie,
    should_persist_auth_cookie,
)


def serialize_user(user: User) -> dict:
    """Serialize a User ORM row into the public response shape.

    Uses an explicit Pydantic schema (whitelisted fields) instead of
    ``User.to_dict()`` so the response contract is stable and adding a column
    to the model can never leak into API output. ``token_version`` and any
    other sensitive columns are excluded by construction.
    """
    return UserResponse.model_validate(user).model_dump()


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
