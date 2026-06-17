import logging

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from domains.user.application.services.auth import validate_auth_token
from infrastructure.auth.jwt import AUTH_COOKIE_NAME, clear_auth_cookie
from infrastructure.http import response

logger = logging.getLogger(__name__)

PUBLIC_EXACT_PATHS = {
    "/api/users/login",
    "/api/users/register",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/video/thumbnail",
}

PUBLIC_PATH_PREFIXES = [
    "/health",
    "/health/ready",
    "/health/live",
]


def is_public_api_path(path: str) -> bool:
    if path in PUBLIC_EXACT_PATHS:
        return True
    if any(path == prefix or path.startswith(prefix + "/") for prefix in PUBLIC_PATH_PREFIXES):
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


class AuthenticationMiddleware:
    """Cookie-based authentication for /api/* routes as a pure ASGI middleware."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        if not path.startswith("/api") or is_public_api_path(path):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        token = request.cookies.get(AUTH_COOKIE_NAME)

        if not token:
            await self._reject(scope, receive, send, TokenMissingError(), request)
            return

        try:
            validate_auth_token(token)
        except Exception:
            # API boundary -- convert to HTTP error response
            logger.error("Invalid token", exc_info=True)
            await self._reject(scope, receive, send, TokenExpiredError(), request, clear_cookie=True)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(
        scope: Scope,
        receive: Receive,
        send: Send,
        error: AuthenticationError,
        request: Request,
        *,
        clear_cookie: bool = False,
    ) -> None:
        unauthorized_response = response.unauthorized(error.detail)
        if clear_cookie:
            clear_auth_cookie(unauthorized_response, request)
        await unauthorized_response(scope, receive, send)
