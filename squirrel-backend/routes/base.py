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

from core.config import settings
from core.database import engine
from routes.middleware.auth import (
    AuthMiddleware,
    AuthenticationError,
    TokenMissingError,
    TokenExpiredError,
)
from routes.middleware.trace import TraceMiddleware
from routes.health import router as health_router
from routes.subscription import router as subscription_router
from routes.user import router as user_router
from routes.video import router as video_router
from routes.video_history import router as video_history_router
from routes.video_interaction import router as video_interaction_router
from routes.system_config import router as system_config_router
from routes.plugins import router as plugins_router
from routes.logs import router as logs_router
from routes.connectivity import router as connectivity_router
from routes.metrics import router as metrics_router
from routes.scheduler import router as scheduler_router

logger = logging.getLogger()


def create_app() -> FastAPI:
    app = FastAPI(exception_handlers=None)

    @app.on_event("startup")
    async def _bootstrap_scheduled_tasks() -> None:
        try:
            from services.scheduled_task_bootstrap import ensure_system_tasks
            ensure_system_tasks()
        except Exception as e:
            logger.error(f"Failed to bootstrap scheduled tasks: {e}", exc_info=True)


    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        """处理认证错误"""
        logger.error(f"AuthenticationError: {exc.detail}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"code": -1, "msg": exc.detail}
        )

    async def http_exception_handler(request: Request, exc: Union[StarletteHTTPException, FastAPIHTTPException]):
        """处理 HTTP 异常"""
        logger.error(f"HTTPException: {exc.detail}", exc_info=True)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": -1, "msg": exc.detail}
        )

    async def default_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""
        logger.error(f"DefaultException: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": -1, "msg": "服务器内部错误"}
        )

    # 配置 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "Authorization", "X-Trace-Id"],
        expose_headers=["X-Trace-Id"],
    )

    # 配置链路追踪中间件（必须在认证中间件之前，确保所有请求都有 trace_id）
    app.add_middleware(TraceMiddleware)
    
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
        }
    )

    # 注册路由
    app.include_router(health_router)  # 健康检查路由（无需认证）
    app.include_router(metrics_router)  # 监控指标路由
    app.include_router(video_router)
    app.include_router(subscription_router)
    app.include_router(user_router)
    app.include_router(video_history_router)
    app.include_router(video_interaction_router)
    app.include_router(system_config_router)
    app.include_router(plugins_router)
    app.include_router(logs_router)
    app.include_router(connectivity_router)
    app.include_router(scheduler_router)

    # 开发环境也需要挂载 thumbnails 静态文件
    _mount_thumbnails(app)

    # 生产环境：挂载静态文件和 SPA 路由
    if not settings.is_dev:
        _mount_static_files(app)
        _register_spa_route(app)

    return app


def _mount_thumbnails(app: FastAPI) -> None:
    thumbnails_dir = str(settings.thumbnails_dir)
    if os.path.exists(thumbnails_dir):
        app.mount("/static/thumbnails", StaticFiles(directory=thumbnails_dir), name="thumbnails")
        logger.info(f"Thumbnails mounted: {thumbnails_dir}")


def _mount_static_files(app: FastAPI) -> None:
    static_dir = str(settings.static_dir)
    
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Static files mounted: {static_dir}")
    else:
        logger.warning(f"Static directory not found: {static_dir}, skipping static files mounting")


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
            content={"code": -1, "msg": "Frontend static files not found"}
        )


app = create_app()
