import asyncio
import json
import os
import re
import stat
import time
from email.utils import formatdate
from mimetypes import guess_type

from fastapi import APIRouter, Query
from sqlmodel import select, col
from sse_starlette import EventSourceResponse
from starlette.requests import Request
from starlette.responses import StreamingResponse

import common.response as response
from common import constants
from core.cache import RedisClient
from core.database import get_session
from downloader.downloader import Downloader
from meta.factory import VideoFactory
from models.download_task import DownloadTask
from schemas.task import DownloadRequest, DownloadChangeStateRequest
from services.task_service import TaskService

router = APIRouter(tags=['下载任务接口'])


@router.post("/api/task/download")
def start_download(req: DownloadRequest):
    TaskService.start_download(req.url)
    return response.success()


@router.post("/api/task/retry")
def retry_download(req: DownloadChangeStateRequest):
    TaskService.retry_download(req.task_id)
    return response.success()


@router.post("/api/task/pause")
def pause_download(req: DownloadChangeStateRequest):
    TaskService.pause_download(req.task_id)
    return response.success()


@router.post("/api/task/delete")
def delete_download(req: DownloadChangeStateRequest):
    TaskService.delete_download(req.task_id)
    return response.success()


@router.get("/api/task/list")
def get_tasks(
        status: str = Query(None, description="任务状态"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    task_convert_list, total_tasks = TaskService.list_tasks(status, page, page_size)
    return response.success({
        "page": page,
        "pageSize": page_size,
        "data": task_convert_list,
        "total": total_tasks,
    })


@router.get("/api/task/progress")
async def get_tasks_progress(task_ids: str):
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
                await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.get("/api/task/new_task_notification")
async def new_task_notification(latest_task_id: int = Query(default=0)):
    client = RedisClient.get_instance().client

    async def event_generator():
        while True:
            with get_session() as session:
                new_tasks = session.exec(select(DownloadTask).where(DownloadTask.task_id > latest_task_id).order_by(
                    col(DownloadTask.task_id).desc()).limit(30)).all()
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


@router.get("/api/task/video/play/{task_id}")
def play_video(request: Request, task_id: str):
    with get_session() as s:
        download_task = s.query(DownloadTask).filter(DownloadTask.task_id == task_id).first()
        s.expunge(download_task)

    base_info = Downloader.get_video_info(download_task.url)
    video = VideoFactory.create_video(download_task.url, base_info)
    output_dir = video.get_download_full_path()

    ext_names = ['.mp4', '.mkv', '.webm']
    filename = video.get_valid_filename()

    files = os.listdir(output_dir)
    video_path = None
    for file in files:
        if file.startswith(filename) and any(file.endswith(ext) for ext in ext_names):
            video_path = os.path.join(output_dir, file)
            break

    stat_result = os.stat(video_path)
    content_type, encoding = guess_type(video_path)
    content_type = content_type or 'application/octet-stream'
    range_str = request.headers.get('range', '')
    range_match = re.search(r'bytes=(\d+)-(\d+)', range_str, re.S) or re.search(r'bytes=(\d+)-', range_str, re.S)
    if range_match:
        start_bytes = int(range_match.group(1))
        end_bytes = int(range_match.group(2)) if range_match.lastindex == 2 else stat_result.st_size - 1
    else:
        start_bytes = 0
        end_bytes = stat_result.st_size - 1

    content_length = stat_result.st_size - start_bytes if stat.S_ISREG(stat_result.st_mode) else stat_result.st_size
    # 打开文件从起始位置开始分片读取文件
    return StreamingResponse(
        file_iterator(video_path, start_bytes, 1024 * 1024 * 1),
        media_type=content_type,
        headers={
            'accept-ranges': 'bytes',
            'connection': 'keep-alive',
            'content-length': str(content_length),
            'content-range': f'bytes {start_bytes}-{end_bytes}/{stat_result.st_size}',
            'last-modified': formatdate(stat_result.st_mtime, usegmt=True),
        },
        status_code=206 if start_bytes > 0 else 200
    )


def file_iterator(file_path, offset, chunk_size):
    """
    文件生成器
    :param file_path: 文件绝对路径
    :param offset: 文件读取的起始位置
    :param chunk_size: 文件读取的块大小
    :return: yield
    """
    with open(file_path, 'rb') as f:
        f.seek(offset, os.SEEK_SET)
        while True:
            data = f.read(chunk_size)
            if data:
                yield data
            else:
                break
