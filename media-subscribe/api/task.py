import asyncio
import json
import logging
import os
import re
import stat
import time
from email.utils import formatdate
from mimetypes import guess_type

from fastapi import Query, APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sse_starlette.sse import EventSourceResponse
from starlette.responses import StreamingResponse

import common.response as response
from common import constants
from common.cache import RedisClient
from common.database import get_session
from downloader.downloader import Downloader
from meta.video import VideoFactory
from model.download_task import DownloadTask
from service import download_service

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=['下载任务接口']
)


class DownloadRequest(BaseModel):
    url: str


@router.post("/api/task/download")
def start_download(req: DownloadRequest):
    download_service.start(req.url, if_only_extract=False)
    return response.success()


class DownloadChangeStateRequest(BaseModel):
    task_id: int


@router.post("/api/task/retry")
def start_download(req: DownloadChangeStateRequest):
    with get_session() as s:
        download_task = s.query(DownloadTask).filter(DownloadTask.task_id == req.task_id).first()
        download_task.status = 'PENDING'
        download_task.retry = download_task.retry + 1
        s.commit()
        download_service.start(download_task.url, if_only_extract=False, if_retry=True, if_manual_retry=True)

    return response.success()


@router.post("/api/task/pause")
def start_download(req: DownloadChangeStateRequest):
    with get_session() as s:
        download_task = s.query(DownloadTask).filter(DownloadTask.task_id == req.task_id).first()
        download_task.status = 'PAUSED'
        s.commit()
        download_service.stop(download_task.task_id)

    return response.success()


@router.post("/api/task/delete")
def start_download(req: DownloadChangeStateRequest):
    with get_session() as s:
        download_task = s.query(DownloadTask).filter(DownloadTask.task_id == req.task_id).first()
        s.delete(download_task)
        s.commit()
        download_service.stop(download_task.task_id)

    return response.success()


class DownloadTaskListRequest(BaseModel):
    page: str
    page_size: str


@router.get("/api/task/list")
def get_tasks(
        status: str = Query(None, description="任务状态"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    task_page = get_updated_task_list(status, page, page_size)
    return response.success(data=task_page)


def get_updated_task_list(status: str = None, page: int = 1, page_size: int = 10):
    with get_session() as s:
        base_query = s.query(DownloadTask).filter(DownloadTask.title != '')
        if status:
            base_query = base_query.filter(DownloadTask.status == status)
        total_tasks = base_query.count()
        offset = (page - 1) * page_size

        tasks = (base_query
                 .order_by(DownloadTask.created_at.desc())
                 .offset(offset)
                 .limit(page_size))

        task_convert_list = []
        for task in tasks:
            task_id = task.task_id

            # 下载信息缓存到redis中
            client = RedisClient.get_instance().client
            downloaded_size = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'downloaded_size')
            total_size = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'total_size')
            speed = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'speed')
            eta = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'eta')
            percent = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'percent')

            task_convert_list.append({
                "id": task.task_id,
                "thumbnail": task.thumbnail,
                "status": task.status,
                "title": task.title,
                "channel_name": task.channel_name,
                "channel_avatar": task.channel_avatar,
                "downloaded_size": int(downloaded_size) if downloaded_size else 0,
                "total_size": int(total_size) if total_size else 0,
                "speed": speed or '未知',
                "eta": eta or '未知',
                "percent": percent or '未知',
                "error_message": task.error_message,
                "retry": task.retry,
                "updated_at": task.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "created_at": task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

    # 使用指定字段组织返回数据
    return {
        "page": page,
        "pageSize": page_size,
        "data": task_convert_list,
        "total": total_tasks,
    }


@router.get("/api/task/video/play/{task_id}")
def play_video(request: Request, task_id: str):
    with get_session() as s:
        download_task = s.query(DownloadTask).filter(DownloadTask.task_id == task_id).first()
        s.expunge(download_task)

    base_info = Downloader.get_video_info(download_task.url)
    video = VideoFactory.create_video(download_task.url, base_info)
    output_dir = video.get_download_full_path()
    filename = video.get_valid_filename() + ".mp4"
    video_path = os.path.join(output_dir, filename)

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
        file_iterator(video_path, start_bytes, 1024 * 1024 * 1),  # 每次读取 1M
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


@router.get("/api/task/progress")
async def tasks_progress(task_ids: str):
    client = RedisClient.get_instance().client
    task_ids_list = task_ids.split(',')

    async def event_generator():
        while True:
            tasks_progress = []
            for task_id in task_ids_list:
                progress = client.hgetall(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}')
                with get_session() as s:
                    task = s.query(DownloadTask).filter(DownloadTask.task_id == task_id).first()
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
                new_tasks = session.query(DownloadTask).filter(DownloadTask.task_id > latest_task_id).order_by(
                    desc(DownloadTask.task_id)).limit(10).all()

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
