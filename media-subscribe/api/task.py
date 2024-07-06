import logging
import os
import common.response as response
from fastapi import HTTPException, Query, APIRouter
from pydantic import BaseModel

from downloader.downloader import Downloader
from meta.video import VideoFactory
from model.download_task import DownloadTask
from service import download_service

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=['任务接口']
)


class DownloadRequest(BaseModel):
    url: str


@router.post("/api/task/download")
def start_download(req: DownloadRequest):
    url = req.url
    download_service.start_download(url)

    return response.success()


class DownloadTaskListRequest(BaseModel):
    page: str
    page_size: str


@router.get("/api/task/list")
def get_tasks(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    task_page = get_updated_task_list(page, page_size)
    return response.success(data=task_page)


def get_updated_task_list(page: int = 1, page_size: int = 10):
    total_tasks = DownloadTask.select().where(DownloadTask.title != '').count()
    offset = (page - 1) * page_size

    tasks = (DownloadTask
             .select()
             .where(DownloadTask.title != '')
             .order_by(DownloadTask.created_at.desc())
             .offset(offset)
             .limit(page_size))

    task_convert_list = [
        {
            "id": task.task_id,
            "thumbnail": task.thumbnail,
            "status": task.status,
            "title": task.title,
            "downloaded_size": task.downloaded_size or 0,
            "total_size": task.total_size or 0,
            "speed": task.speed or '未知',
            "eta": task.eta or '未知',
            "percent": task.percent or '未知',
            "error_message": task.error_message,
            "created_at": task.created_at,
        } for task in tasks
    ]

    # 使用指定字段组织返回数据
    return {
        "page": page,
        "pageSize": page_size,
        "data": task_convert_list,
        "total": total_tasks,
    }


@router.get("/api/task/video/play/{task_id}")
async def play_video(task_id: str):
    download_task = DownloadTask.select().where(DownloadTask.task_id == task_id).first()
    base_info = Downloader.get_video_info(download_task.url)
    video = VideoFactory.create_video(download_task.url, base_info)
    output_dir = video.get_download_full_path()
    filename = video.get_valid_filename() + ".mp4"
    video_path = os.path.join(output_dir, filename)

    # 检查视频文件是否存在
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="视频文件未找到")

    # 使用Starlette的StreamingResponse直接发送视频流
    from fastapi.responses import StreamingResponse

    async def video_streamer(path):
        with open(path, "rb") as video_file:
            while True:
                chunk = video_file.read(1024)  # Read 1KB at a time
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(video_streamer(video_path), media_type="video/mp4")
