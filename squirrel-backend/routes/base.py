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
from routes.subscription import router as subscription_router
from routes.task import router as task_router
from routes.user import router as user_router
from routes.video import router as video_router
from routes.video_history import router as video_history_router
from routes.video_interaction import router as video_interaction_router
from routes.system_config import router as system_config_router
from routes.plugins import router as plugins_router

logger = logging.getLogger()


def create_app() -> FastAPI:
    app = FastAPI(exception_handlers=None)


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
        allow_headers=["*", "Authorization"],
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
        }
    )

    # 注册路由
    app.include_router(video_router)
    app.include_router(task_router)
    app.include_router(subscription_router)
    app.include_router(user_router)
    app.include_router(video_history_router)
    app.include_router(video_interaction_router)
    app.include_router(system_config_router)
    app.include_router(plugins_router)

    # 生产环境：挂载静态文件和 SPA 路由
    if not settings.is_dev:
        _mount_static_files(app)
        _register_spa_route(app)

    return app


def _mount_static_files(app: FastAPI) -> None:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, "static")
    
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Static files mounted: {static_dir}")
    else:
        logger.warning(f"Static directory not found: {static_dir}, skipping static files mounting")


def _register_spa_route(app: FastAPI) -> None:

    @app.get("/{full_path:path}", name="spa")
    async def serve_spa(full_path: str):
        """服务于前端 SPA 的路由处理器"""
        file_static_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "static"
        )
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
