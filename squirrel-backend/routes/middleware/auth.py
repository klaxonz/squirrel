import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from common import response
from services.auth_service import validate_auth_token
from utils.jwt_helper import AUTH_COOKIE_NAME, clear_auth_cookie

logger = logging.getLogger(__name__)

PUBLIC_PATH_PREFIXES = [
    "/api/users/login",
    "/api/users/register",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/video/thumbnail",
    "/health",
    "/health/ready",
    "/health/live",
]


def is_public_api_path(path: str) -> bool:
    if any(path.startswith(public_path) for public_path in PUBLIC_PATH_PREFIXES):
        return True
    if path.startswith("/api/sites/") and path.endswith("/icon"):
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


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, public_paths: list[str] = None):
        super().__init__(app)
        self.public_paths = public_paths or list(PUBLIC_PATH_PREFIXES)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith("/api") or is_public_api_path(path):
            return await call_next(request)

        token = request.cookies.get(AUTH_COOKIE_NAME)
        if not token:
            return self._unauthorized_response(TokenMissingError())

        try:
            validate_auth_token(token)
        except Exception:
            # API boundary -- convert to HTTP error response
            logger.error("Invalid token", exc_info=True)
            return self._unauthorized_response(TokenExpiredError(), request=request, clear_cookie=True)
        return await call_next(request)

    @staticmethod
    def _unauthorized_response(error: AuthenticationError, request: Request | None = None, clear_cookie: bool = False):
        unauthorized_response = response.unauthorized(error.detail)
        if clear_cookie:
            clear_auth_cookie(unauthorized_response, request)
        return unauthorized_response

