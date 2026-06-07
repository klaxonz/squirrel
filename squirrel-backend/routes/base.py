import logging
import os
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from common.response import ErrorCode
from core.config import settings
from routes.connectivity import router as connectivity_router
from routes.health import router as health_router
from routes.logs import router as logs_router
from routes.middleware.access_log import AccessLogMiddleware
from routes.middleware.auth import (
    AuthenticationError,
    AuthMiddleware,
    TokenExpiredError,
    TokenMissingError,
)
from routes.middleware.trace import RequestContextMiddleware
from routes.music import router as music_router
from routes.playlist import router as playlist_router
from routes.rss import router as rss_router
from routes.scheduler import router as scheduler_router
from routes.search import router as search_router
from routes.site_cookies import router as site_cookies_router
from routes.site_runtimes import router as site_runtimes_router
from routes.sites import router as sites_router
from routes.subscription import router as subscription_router
from routes.system_config import router as system_config_router
from routes.user import router as user_router
from routes.video import router as video_router
from routes.video_clip_marker import router as video_clip_marker_router
from routes.video_history import router as video_history_router
from routes.video_interaction import router as video_interaction_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(exception_handlers=None)

    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        """处理认证错误"""
        logger.error("AuthenticationError: %s", exc.detail, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"code": ErrorCode.UNAUTHORIZED, "msg": exc.detail},
        )

    async def http_exception_handler(request: Request, exc: StarletteHTTPException | FastAPIHTTPException):
        """处理 HTTP 异常"""
        logger.error("HTTPException: %s", exc.detail, exc_info=True)
        code = exc.status_code if exc.status_code in {
            ErrorCode.PARAM_ERROR, ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN, ErrorCode.NOT_FOUND,
            ErrorCode.SERVER_ERROR,
        } else ErrorCode.UNKNOWN_ERROR
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "msg": exc.detail},
        )

    async def default_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""
        logger.error("DefaultException: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": ErrorCode.SERVER_ERROR, "msg": "服务器内部错误"},
        )

    # 配置认证中间件
    app.add_middleware(AuthMiddleware)

    # 配置异常处理中间件
    app.add_middleware(
        ExceptionMiddleware,
        handlers={
            FastAPIHTTPException: http_exception_handler,
            StarletteHTTPException: http_exception_handler,
            Exception: default_exception_handler,
            AuthenticationError: authentication_error_handler,
            TokenMissingError: authentication_error_handler,
            TokenExpiredError: authentication_error_handler,
        },
    )

    # 应用层访问日志需要运行在请求上下文内，并覆盖认证/异常分支。
    app.add_middleware(AccessLogMiddleware)

    # 请求上下文必须最外层，确保所有后续日志都能读取 trace_id。
    app.add_middleware(RequestContextMiddleware)

    # Configure CORS after auth middleware so it wraps preflight and error responses.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "Authorization", "X-Trace-Id"],
        expose_headers=["X-Trace-Id"],
    )

    # 注册路由
    app.include_router(health_router)  # 健康检查路由（无需认证）
    app.include_router(video_router)
    app.include_router(video_clip_marker_router)
    app.include_router(subscription_router)
    app.include_router(user_router)
    app.include_router(video_history_router)
    app.include_router(video_interaction_router)
    app.include_router(playlist_router)
    app.include_router(system_config_router)
    app.include_router(site_runtimes_router)
    app.include_router(sites_router)
    app.include_router(site_cookies_router)
    app.include_router(logs_router)
    app.include_router(search_router)
    app.include_router(connectivity_router)
    app.include_router(scheduler_router)
    app.include_router(rss_router)
    app.include_router(music_router)

    # 开发环境也需要挂载可单独配置的静态资源目录
    _mount_thumbnails(app)
    _mount_clip_marker_previews(app)

    # 生产环境：挂载静态文件和 SPA 路由
    if not settings.is_dev:
        _mount_static_files(app)
        _register_spa_route(app)

    return app


def _mount_thumbnails(app: FastAPI) -> None:
    thumbnails_dir = str(settings.thumbnails_dir)
    if os.path.exists(thumbnails_dir):
        app.mount("/static/thumbnails", StaticFiles(directory=thumbnails_dir), name="thumbnails")
        logger.info("Thumbnails mounted: %s", thumbnails_dir)


def _mount_clip_marker_previews(app: FastAPI) -> None:
    clip_marker_previews_dir = str(settings.clip_marker_previews_dir)
    if os.path.exists(clip_marker_previews_dir):
        app.mount("/static/clip-markers", StaticFiles(directory=clip_marker_previews_dir), name="clip-marker-previews")
        logger.info("Clip marker previews mounted: %s", clip_marker_previews_dir)


def _mount_static_files(app: FastAPI) -> None:
    static_dir = str(settings.static_dir)

    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info("Static files mounted: %s", static_dir)
    else:
        logger.warning("Static directory not found: %s, skipping static files mounting", static_dir)


def _register_spa_route(app: FastAPI) -> None:

    @app.get("/{full_path:path}", name="spa")
    async def serve_spa(full_path: str):
        """服务于前端 SPA 的路由处理器"""
        file_static_dir = str(settings.static_dir)

        static_file = Path(file_static_dir) / full_path

        # 如果是静态文件，直接返回
        if static_file.exists() and static_file.is_file():
            return FileResponse(static_file)

        # 否则返回 index.html（SPA 路由由前端处理）
        index_file = Path(file_static_dir) / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

        # 如果静态文件目录不存在，返回友好提示
        return JSONResponse(
            status_code=404,
            content={"code": ErrorCode.NOT_FOUND, "msg": "Frontend static files not found"},
        )
