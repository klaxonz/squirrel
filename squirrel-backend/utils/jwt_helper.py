import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from fastapi import Cookie, HTTPException, Response, status

from models.user import User
from services import user_service

logger = logging.getLogger()

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
AUTH_COOKIE_NAME = 'squirrel_auth'
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create JWT access token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=AUTH_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite='lax',
        path='/',
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path='/',
        httponly=True,
        secure=True,
        samesite='lax',
    )


async def get_current_user(token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> Optional[User]:
    """
    Validate token and return current user with config preloaded
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get('sub')
        if subject is None:
            raise credentials_exception
        user_id = int(subject)
        if user_id is None:
            raise credentials_exception
        user = user_service.get_user_by_id(user_id)
        if user is None:
            raise credentials_exception
        
        # 预加载 user_config，避免后续重复查询
        # 将 config 作为临时属性附加到 user 对象上
        from services import user_config_service
        user._cached_config = user_config_service.get_config(user_id)
        
        return user
    except JWTError:
        raise credentials_exception


def decode_token(token: str) -> dict:
    """
    Decode JWT token
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        logger.error("Invalid token", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
