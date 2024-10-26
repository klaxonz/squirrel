import asyncio
import json
import time

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, col
from sse_starlette import EventSourceResponse

import common.response as response
from common import constants
from core.cache import RedisClient
from core.database import get_session
from model.download_task import DownloadTask
from schemas.task import DownloadRequest, DownloadChangeStateRequest
from services.task_service import TaskService

router = APIRouter(tags=['下载任务接口'])


@router.post("/api/task/download")
def start_download(req: DownloadRequest, session: Session = Depends(get_session)):
    task_service = TaskService(session)
    task_service.start_download(req.url)
    return response.success()


@router.post("/api/task/retry")
def retry_download(req: DownloadChangeStateRequest, session: Session = Depends(get_session)):
    task_service = TaskService(session)
    success = task_service.retry_download(req.task_id)
    return response.success() if success else response.error("Task not found")


@router.post("/api/task/pause")
def pause_download(req: DownloadChangeStateRequest, session: Session = Depends(get_session)):
    task_service = TaskService(session)
    success = task_service.pause_download(req.task_id)
    return response.success() if success else response.error("Task not found")


@router.post("/api/task/delete")
def delete_download(req: DownloadChangeStateRequest, session: Session = Depends(get_session)):
    task_service = TaskService(session)
    success = task_service.delete_download(req.task_id)
    return response.success() if success else response.error("Task not found")


@router.get("/api/task/list")
def get_tasks(
        status: str = Query(None, description="任务状态"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page"),
        session: Session = Depends(get_session)
):
    task_service = TaskService(session)
    task_convert_list, total_tasks = task_service.list_tasks(status, page, page_size)
    return response.success({
        "page": page,
        "pageSize": page_size,
        "data": task_convert_list,
        "total": total_tasks,
    })


@router.get("/api/task/progress")
async def tasks_progress(task_ids: str):
    client = RedisClient.get_instance().client
    task_ids_list = task_ids.split(',')

    async def event_generator():
        while True:
            with get_session() as session:
                tasks_progress = []
                for task_id in task_ids_list:
                    progress = client.hgetall(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}')
                    task = session.exec(select(DownloadTask).where(DownloadTask.task_id == task_id)).first()
                    task_status = task.status if task else None

                    if progress:
                        current_type = progress.get('current_type', 'unknown')
                        data = {
                            "task_id": int(task_id),
                            "status": task_status,
                            "current_type": current_type,
                            "downloaded_size": int(progress.get('downloaded_size', 0)),
                            "total_size": int(progress.get('total_size', 0)),
                            "speed": progress.get('speed', '未知'),
                            "eta": progress.get('eta', '未知'),
                            "percent": progress.get('percent', '未知'),
                        }
                        tasks_progress.append(data)

                yield {
                    "event": "message",
                    "data": json.dumps(tasks_progress)
                }
                await asyncio.sleep(1)  # 每秒更新一次

    return EventSourceResponse(event_generator())


@router.get("/api/task/new_task_notification")
async def new_task_notification(latest_task_id: int = Query(default=0)):
    client = RedisClient.get_instance().client

    async def event_generator():
        while True:
            with get_session() as session:
                new_tasks = session.exec(select(DownloadTask).where(DownloadTask.task_id > latest_task_id).order_by(
                    col(DownloadTask.task_id).desc()).limit(30)).all()
                print("new_tasks", new_tasks)
                if new_tasks:
                    new_task_data = []
                    for task in new_tasks:
                        # 获取下载进度信息
                        progress = client.hgetall(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task.task_id}')
                        downloaded_size = int(progress.get('downloaded_size', 0))
                        total_size = int(progress.get('total_size', 0))
                        speed = progress.get('speed', '未知')
                        eta = progress.get('eta', '未知')
                        percent = progress.get('percent', '未知')

                        new_task_data.append({
                            "id": task.task_id,
                            "thumbnail": task.thumbnail,
                            "status": task.status,
                            "title": task.title,
                            "channel_name": task.channel_name,
                            "channel_avatar": task.channel_avatar,
                            "downloaded_size": downloaded_size,
                            "total_size": total_size,
                            "speed": speed,
                            "eta": eta,
                            "percent": percent,
                            "error_message": task.error_message,
                            "retry": task.retry,
                            "updated_at": task.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                            "created_at": task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        })

                    yield {
                        "event": "message",
                        "data": json.dumps(new_task_data)
                    }
                    await asyncio.sleep(1)  # 每秒检查一次

                else:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": time.time()})
                    }
                    await asyncio.sleep(1)  # 每秒检查一次

    return EventSourceResponse(event_generator())
