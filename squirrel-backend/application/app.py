import logging
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from application.lifespan import lifespan
from application.routes.health import router as health_router
from application.routes.logs import router as logs_router
from domains.music.interfaces.http import router as music_router
from domains.playlist.interfaces.http import router as playlist_router
from domains.rss.interfaces.http import router as rss_router
from domains.subscription.interfaces.http import router as subscription_router
from domains.system.interfaces.http.system_config import router as system_config_router
from domains.user.interfaces.http import router as user_router
from domains.user.interfaces.http.search import router as search_router
from domains.video.interfaces.http import router as video_router
from domains.video.interfaces.http.clip_marker import router as video_clip_marker_router
from domains.video.interfaces.http.history import router as video_history_router
from domains.video.interfaces.http.interaction import router as video_interaction_router
from infrastructure.config.settings import settings
from infrastructure.http import response
from infrastructure.http.middleware.access_log import AccessLogMiddleware
from infrastructure.http.middleware.auth import (
    AuthenticationError,
    AuthenticationMiddleware,
    TokenExpiredError,
    TokenMissingError,
)
from infrastructure.http.middleware.trace import RequestContextMiddleware
from infrastructure.http.response import ErrorCode
from infrastructure.scheduling.routes import router as scheduler_router
from infrastructure.site_catalog.routes.connectivity_batch import router as connectivity_router
from infrastructure.site_catalog.routes.site_cookies_bulk_import import router as site_cookies_router
from infrastructure.site_catalog.routes.site_plugins import router as site_plugins_router
from infrastructure.site_catalog.routes.sites_catalog import router as sites_router

logger = logging.getLogger(__name__)

# HTTP 状态码 → 业务错误码映射;未列出的状态码归 UNKNOWN_ERROR。
# 与 infrastructure.http.response._http_status_for_code 方向相反:那边是 code→status,
# 这里需要从 exc.status_code 反查业务码,故本地维护。
_STATUS_CODE_TO_ERROR_CODE: dict[int, int] = {
    status.HTTP_400_BAD_REQUEST: ErrorCode.PARAM_ERROR,
    status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_500_INTERNAL_SERVER_ERROR: ErrorCode.SERVER_ERROR,
}


async def authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    logger.error("AuthenticationError: %s", exc.detail, exc_info=True)
    return response.error(exc.detail, ErrorCode.UNAUTHORIZED)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # exc.status_code 可能是任意值,不能用 response.error()(它按业务码反推 status),
    # 故手写 JSONResponse 以保留原始 HTTP 状态码。
    logger.error("HTTPException: %s", exc.detail, exc_info=True)
    code = _STATUS_CODE_TO_ERROR_CODE.get(exc.status_code, ErrorCode.UNKNOWN_ERROR)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "msg": exc.detail},
    )


async def default_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("DefaultException: %s", exc, exc_info=True)
    return response.server_error("服务器内部错误")


def create_app() -> FastAPI:
    app = FastAPI(exception_handlers=None, lifespan=lifespan)
    _register_middleware(app)
    _register_routers(app)
    _mount_static_assets(app)
    return app


def _register_middleware(application: FastAPI) -> None:
    """Register middleware. Starlette executes them in reverse-add order (last added = outermost):
    request flow is CORS -> RequestContext -> AccessLog -> Exception -> Authentication.
    """
    application.add_middleware(AuthenticationMiddleware)
    application.add_middleware(
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
    application.add_middleware(AccessLogMiddleware)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "Authorization", "X-Trace-Id"],
        expose_headers=["X-Trace-Id"],
    )


# 注册顺序即路由匹配顺序;每条路由自带前缀(prefix 互不重叠,无需聚合 /api/v1)。
_ROUTERS: tuple[APIRouter, ...] = (
    health_router,
    video_router,
    video_clip_marker_router,
    video_history_router,
    video_interaction_router,
    subscription_router,
    user_router,
    search_router,
    playlist_router,
    music_router,
    rss_router,
    system_config_router,
    site_plugins_router,
    sites_router,
    site_cookies_router,
    connectivity_router,
    scheduler_router,
    logs_router,
)


def _register_routers(application: FastAPI) -> None:
    for router in _ROUTERS:
        application.include_router(router)


def _mount_static_assets(application: FastAPI) -> None:
    _mount_static(application, "/static/thumbnails", settings.thumbnails_dir, "thumbnails")
    _mount_static(application, "/static/clip-markers", settings.clip_marker_previews_dir, "clip-marker-previews")
    if not settings.is_dev:
        _mount_static(application, "/static", settings.static_dir, "static")
        _register_spa_route(application)


def _mount_static(application: FastAPI, path: str, directory: Path, name: str) -> None:
    """Mount a StaticFiles app at `path` if `directory` exists, else warn and skip."""
    if not directory.exists():
        logger.warning("Static directory not found: %s, skipping %s mounting", directory, name)
        return
    application.mount(path, StaticFiles(directory=directory), name=name)
    logger.info("%s mounted: %s", name, directory)


def _register_spa_route(application: FastAPI) -> None:

    @application.get("/{full_path:path}", name="spa")
    async def serve_spa(full_path: str):
        static_dir = settings.static_dir

        static_file = static_dir / full_path
        if static_file.is_file():
            return FileResponse(static_file)

        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

        return response.not_found("Frontend static files not found")


app = create_app()
