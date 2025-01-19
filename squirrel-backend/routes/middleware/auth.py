from typing import List
from fastapi import Request, status
from fastapi.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from utils.jwt_helper import decode_token
import logging

logger = logging.getLogger()


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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="请先登录",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth.split(" ")[1]
        try:
            decode_token(token)
            return await call_next(request)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="登录已过期，请重新登录",
                headers={"WWW-Authenticate": "Bearer"},
            )
