import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse
from starlette.staticfiles import StaticFiles

from .channel import router as channel_router
from .channel_video import router as channel_video_router
from .settings import router as settings_router
from .task import router as task_router
from .video_history import router as video_history_router
from .podcast import router as podcast_router

logger = logging.getLogger(__name__)
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
app.include_router(channel_router)
app.include_router(channel_video_router)
app.include_router(video_history_router)
app.include_router(podcast_router)

# 挂载静态文件
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(base_dir, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

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
    static_file = Path(static_dir) / full_path
    
    if static_file.exists() and static_file.is_file():
        return FileResponse(static_file)
    
    return FileResponse(Path(static_dir) / "index.html")

