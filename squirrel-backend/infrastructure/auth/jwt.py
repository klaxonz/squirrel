import logging
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, Response, status
from jose import JWTError, jwt

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

ALGORITHM = 'HS256'
AUTH_COOKIE_NAME = 'squirrel_auth'
PERSISTENT_AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
TOKEN_VERSION_CLAIM = 'tv'
REMEMBER_ME_CLAIM = 'rm'


def _get_secret_key() -> str:
    return settings.JWT_SECRET_KEY


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )


def create_access_token(payload: dict, expires_delta: timedelta | None = None):
    """Create JWT access token"""
    to_encode = payload.copy()
    expire = datetime.now() + expires_delta if expires_delta else datetime.now() + timedelta(minutes=15)

    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, _get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def _should_use_secure_cookie(request: Request | None) -> bool:
    if request is None:
        return False

    forwarded_proto = str(request.headers.get('x-forwarded-proto') or '').split(',', 1)[0].strip().lower()
    if forwarded_proto:
        return forwarded_proto == 'https'

    return request.url.scheme == 'https'


def set_auth_cookie(
    response: Response,
    token: str,
    request: Request | None = None,
    *,
    persistent: bool = False,
) -> None:
    secure = _should_use_secure_cookie(request)
    cookie_options = {
        'key': AUTH_COOKIE_NAME,
        'value': token,
        'httponly': True,
        'secure': secure,
        'samesite': 'lax',
        'path': '/',
    }
    if persistent:
        cookie_options['max_age'] = PERSISTENT_AUTH_COOKIE_MAX_AGE

    response.set_cookie(**cookie_options)


def clear_auth_cookie(response: Response, request: Request | None = None) -> None:
    secure = _should_use_secure_cookie(request)
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path='/',
        httponly=True,
        secure=secure,
        samesite='lax',
    )


def should_persist_auth_cookie(token: str | None) -> bool:
    if not token:
        return False

    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
    except (JWTError, TypeError, ValueError):
        return False

    if REMEMBER_ME_CLAIM not in payload:
        return True

    return bool(payload.get(REMEMBER_ME_CLAIM))


def decode_token(token: str) -> dict:
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        logger.error('Invalid token', exc_info=True)
        raise _credentials_exception() from exc
