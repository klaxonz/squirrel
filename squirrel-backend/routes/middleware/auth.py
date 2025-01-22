from typing import List
from fastapi import Request, status
from fastapi.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from utils.jwt_helper import decode_token
import logging

logger = logging.getLogger()


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
        self.public_paths = public_paths or [
            "/api/users/login",
            "/api/users/register",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/video/proxy",
            "/api/video/play",
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith('/api') or any(path.startswith(public_path) for public_path in self.public_paths):
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            raise TokenMissingError()

        token = auth.split(" ")[1]
        try:
            decode_token(token)
            return await call_next(request)
        except Exception:
            raise TokenExpiredError()
