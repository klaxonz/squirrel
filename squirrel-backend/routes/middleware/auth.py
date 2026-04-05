import logging
from typing import List

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from common import response
from utils.jwt_helper import AUTH_COOKIE_NAME, clear_auth_cookie, decode_token

logger = logging.getLogger()

PUBLIC_PATH_PREFIXES = [
    "/api/users/login",
    "/api/users/register",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/video/proxy",
    "/api/video/mpd",
    "/api/video/thumbnail",
    "/health",
    "/health/ready",
    "/health/live",
]


def is_public_api_path(path: str) -> bool:
    if any(path.startswith(public_path) for public_path in PUBLIC_PATH_PREFIXES):
        return True
    if path.startswith('/api/plugins/sites/') and path.endswith('/icon'):
        return True
    return False


class AuthenticationError(Exception):
    """Base authentication exception"""

    def __init__(self, detail: str):
        super().__init__()
        self.detail = detail


class TokenMissingError(AuthenticationError):
    """Raised when authentication token is missing"""

    def __init__(self):
        super().__init__(detail="请先登录")


class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired"""

    def __init__(self):
        super().__init__(detail="登录已过期，请重新登录")


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, public_paths: List[str] = None):
        super().__init__(app)
        self.public_paths = public_paths or list(PUBLIC_PATH_PREFIXES)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith('/api') or is_public_api_path(path):
            return await call_next(request)

        token = request.cookies.get(AUTH_COOKIE_NAME)
        if not token:
            return self._unauthorized_response(TokenMissingError())

        try:
            decode_token(token)
        except Exception:
            logger.error("Invalid token", exc_info=True)
            return self._unauthorized_response(TokenExpiredError(), clear_cookie=True)
        return await call_next(request)

    @staticmethod
    def _unauthorized_response(error: AuthenticationError, clear_cookie: bool = False) -> JSONResponse:
        payload = response.unauthorized(error.detail)
        unauthorized_response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=payload,
        )
        if clear_cookie:
            clear_auth_cookie(unauthorized_response)
        return unauthorized_response

