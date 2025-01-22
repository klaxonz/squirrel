import logging
import os
from pathlib import Path
from typing import Union
from fastapi import FastAPI, status
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse
from starlette.staticfiles import StaticFiles
from common.global_config import IS_DEV
from routes.middleware.auth import AuthMiddleware, AuthenticationError, TokenMissingError, TokenExpiredError
from routes.subscription import router as subscription_router
from routes.task import router as task_router
from routes.user import router as user_router
from routes.video import router as video_router

logger = logging.getLogger()

app = FastAPI(exception_handlers=None)


async def authentication_error_handler(request: Request, exc: AuthenticationError):
    logger.error(f"AuthenticationError: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"code": -1, "msg": exc.detail}
    )


async def http_exception_handler(request: Request, exc: Union[StarletteHTTPException, FastAPIHTTPException]):
    logger.error(f"HTTPException: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": -1, "msg": exc.detail}
    )


async def default_exception_handler(request: Request, exc: Exception):
    logger.error(f"DefaultException: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": -1, "msg": "服务器内部错误"}
    )


# 先添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    ExceptionMiddleware,
    handlers={
        FastAPIHTTPException: http_exception_handler,
        StarletteHTTPException: http_exception_handler,
        Exception: default_exception_handler,
        AuthenticationError: authentication_error_handler,
        TokenMissingError: authentication_error_handler,
        TokenExpiredError: authentication_error_handler,
    }
)

app.include_router(video_router)
app.include_router(task_router)
app.include_router(subscription_router)
app.include_router(user_router)

if not IS_DEV:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

FRONTEND_DEV_HOST = os.getenv("FRONTEND_DEV_HOST", "localhost")
FRONTEND_DEV_PORT = os.getenv("FRONTEND_DEV_PORT", "5173")
FRONTEND_DEV_URL = f"http://{FRONTEND_DEV_HOST}:{FRONTEND_DEV_PORT}"

if not IS_DEV:
    @app.get("/{full_path:path}", name="spa")
    async def serve_spa(full_path: str):
        file_static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
        static_file = Path(file_static_dir) / full_path

        if static_file.exists() and static_file.is_file():
            return FileResponse(static_file)

        return FileResponse(Path(file_static_dir) / "index.html")
