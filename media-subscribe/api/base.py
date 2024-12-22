import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from .channel_video import router as channel_video_router
from .settings import router as settings_router
from .task import router as task_router
from .video_history import router as video_history_router
from .podcast import router as podcast_router
from .subscription import router as subscription_router

logger = logging.getLogger()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(task_router)
app.include_router(settings_router)
app.include_router(channel_video_router)
app.include_router(video_history_router)
app.include_router(podcast_router)
app.include_router(subscription_router)

# 判断是否为开发环境
IS_DEV = os.getenv("ENV", "prod").lower() == "dev"

# 只在生产环境下挂载静态文件
if not IS_DEV:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 在文件开头添加配置
FRONTEND_DEV_HOST = os.getenv("FRONTEND_DEV_HOST", "localhost")
FRONTEND_DEV_PORT = os.getenv("FRONTEND_DEV_PORT", "5173")
FRONTEND_DEV_URL = f"http://{FRONTEND_DEV_HOST}:{FRONTEND_DEV_PORT}"

@app.exception_handler(Exception)
async def default_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 0, "msg": "success"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": "Internal Server Error"}
    )


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # 开发环境下重定向到前端开发服务器
    if IS_DEV:
        return RedirectResponse(
            url=f"{FRONTEND_DEV_URL}/{full_path}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    
    # 生产环境下的处理逻辑
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
    static_file = Path(static_dir) / full_path
    
    if static_file.exists() and static_file.is_file():
        return FileResponse(static_file)
    
    return FileResponse(Path(static_dir) / "index.html")

