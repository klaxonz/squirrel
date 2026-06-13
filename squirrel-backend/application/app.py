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

from infrastructure.config.settings import settings
from domains.music.interfaces.http import router as music_router
from domains.playlist.interfaces.http import router as playlist_router
from application.routes.health import router as health_router
from application.routes.logs import router as logs_router
from infrastructure.http.middleware.access_log import AccessLogMiddleware
from infrastructure.http.middleware.auth import (
    AuthenticationError,
    AuthenticationMiddleware,
    TokenExpiredError,
    TokenMissingError,
)
from infrastructure.http.middleware.trace import RequestContextMiddleware
from domains.rss.interfaces.http import router as rss_router
from infrastructure.scheduling.routes import router as scheduler_router
from shared_kernel.application.response import ErrorCode
from shared_kernel.system.routes.system_config import router as system_config_router
from infrastructure.site_catalog.routes.connectivity_batch import router as connectivity_router
from infrastructure.site_catalog.routes.site_cookies_bulk_import import router as site_cookies_router
from infrastructure.site_catalog.routes.site_runtimes import router as site_runtimes_router
from infrastructure.site_catalog.routes.sites_catalog import router as sites_router
from domains.subscription.interfaces.http import router as subscription_router
from domains.user.interfaces.http import router as user_router
from domains.user.interfaces.http.search import router as search_router
from domains.video.interfaces.http import router as video_router
from domains.video.interfaces.http.clip_marker import router as video_clip_marker_router
from domains.video.interfaces.http.history import router as video_history_router
from domains.video.interfaces.http.interaction import router as video_interaction_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(exception_handlers=None)

    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        logger.error("AuthenticationError: %s", exc.detail, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"code": ErrorCode.UNAUTHORIZED, "msg": exc.detail},
        )

    async def http_exception_handler(request: Request, exc: StarletteHTTPException | FastAPIHTTPException):
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
        logger.error("DefaultException: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": ErrorCode.SERVER_ERROR, "msg": "服务器内部错误"},
        )

    app.add_middleware(AuthenticationMiddleware)

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

    app.add_middleware(AccessLogMiddleware)

    app.add_middleware(RequestContextMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "Authorization", "X-Trace-Id"],
        expose_headers=["X-Trace-Id"],
    )

    app.include_router(health_router)
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

    _mount_thumbnails(app)
    _mount_clip_marker_previews(app)

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
        file_static_dir = str(settings.static_dir)

        static_file = Path(file_static_dir) / full_path

        if static_file.exists() and static_file.is_file():
            return FileResponse(static_file)

        index_file = Path(file_static_dir) / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

        return JSONResponse(
            status_code=404,
            content={"code": ErrorCode.NOT_FOUND, "msg": "Frontend static files not found"},
        )
