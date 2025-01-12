import asyncio
import json
import time

from fastapi import APIRouter, Query
from sqlalchemy import select
from sse_starlette import EventSourceResponse

import common.response as response
from core.database import get_session
from models.task.download_task import DownloadTask
from schemas.task import DownloadRequest, DownloadChangeStateRequest
from services import task_service

router = APIRouter(tags=['下载任务接口'])


@router.post("/api/task/download")
def start_download(req: DownloadRequest):
    task_service.start_download(req.url)
    return response.success()


@router.post("/api/task/retry")
def retry_download(req: DownloadChangeStateRequest):
    task_service.retry_download(req.task_id)
    return response.success()


@router.post("/api/task/pause")
def pause_download(req: DownloadChangeStateRequest):
    task_service.pause_download(req.task_id)
    return response.success()


@router.post("/api/task/delete")
def delete_download(req: DownloadChangeStateRequest):
    task_service.delete_task(req.task_id)
    return response.success()


@router.get("/api/task/list")
def get_tasks(
        status: str = Query(None, description="任务状态"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    task_convert_list, total_tasks = task_service.list_tasks(status, page, page_size)
    return response.success({
        "page": page,
        "pageSize": page_size,
        "data": task_convert_list,
        "total": total_tasks,
    })


@router.get("/api/task/progress")
async def get_tasks_progress(task_ids: str):
    task_ids_split = task_ids.split(',')
    task_ids = []
    for task_id in task_ids_split:
        if task_id != '':
            task_ids.append(int(task_id))

    async def event_generator():
        while True:
            with get_session() as session:
                tasks = []
                if len(task_ids) > 0:
                    tasks = session.scalars(select(DownloadTask).where(DownloadTask.id.in_(task_ids))).all()
                tasks_progress = task_service.generate_task_data(tasks)
                yield {
                    "event": "message",
                    "data": json.dumps(tasks_progress)
                }
                await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.get("/api/task/new_task_notification")
async def new_task_notification(latest_task_id: int = Query(default=0)):
    async def event_generator():
        while True:
            with get_session() as session:
                tasks = session.scalars(select(DownloadTask).where(DownloadTask.id > latest_task_id).order_by(
                    DownloadTask.id.desc()).limit(30)).all()
                if len(tasks) > 0:
                    task_data = task_service.generate_task_data(tasks)
                    yield {
                        "event": "message",
                        "data": json.dumps(task_data)
                    }
                    await asyncio.sleep(1)

                else:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": time.time()})
                    }
                    await asyncio.sleep(1)

    return EventSourceResponse(event_generator())



