import json
import logging
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from common.message_queue import RedisMessageQueue, Message
from common.constants import *
import service.download_service as download_service
from downloader.downloader import Downloader
from meta.video import VideoFactory
from model.channel import Channel, ChannelVideo
from model.download_task import DownloadTask

logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


class DownloadRequest(BaseModel):
    url: str


@app.post("/api/download")
def start_download(req: DownloadRequest):
    try:
        url = req.url
        download_service.start_download(url)

        return {"status": "success", "message": "下载任务已启动"}
    except Exception as e:
        logger.error("下载过程中发生错误", exc_info=True)
        raise HTTPException(status_code=500, detail="下载任务启动失败")


class SubscribeChannelRequest(BaseModel):
    url: str


@app.post("/api/channel/subscribe")
def subscribe_channel(req: SubscribeChannelRequest):
    try:
        subscribe_queue = RedisMessageQueue(queue_name=QUEUE_SUBSCRIBE_TASK)

        task = {
            "url": req.url,
        }

        message = Message(body=json.dumps(task))
        message.save()

        subscribe_queue.enqueue(message)

        return {"status": "success", "message": "订阅成功"}
    except Exception as e:
        logger.error("订阅失败", exc_info=True)
        raise HTTPException(status_code=500, detail="订阅失败")


@app.get("/api/channel/list")
def subscribe_channel(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    try:
        total = Channel.select().count()
        offset = (page - 1) * page_size
        channels = (Channel
                    .select()
                    .order_by(Channel.created_at.desc())
                    .offset(offset)
                    .limit(page_size))

        channel_convert_list = [
            {
                'id': channel.id,
                'channel_id': channel.channel_id,
                'name': channel.name,
                'url': channel.url,
                'if_enable': channel.if_enable,
                'created_at': channel.created_at
            } for channel in channels
        ]

        return {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "data": channel_convert_list
        }

    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@app.get("/api/channel/video/list")
def subscribe_channel(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    try:
        total = ChannelVideo.select().where(ChannelVideo.title != '', ChannelVideo.if_read == 0).count()
        offset = (page - 1) * page_size
        channel_videos = (ChannelVideo
                          .select()
                          .where(ChannelVideo.title != '', ChannelVideo.if_read == 0)
                          .order_by(ChannelVideo.uploaded_at.desc())
                          .offset(offset)
                          .limit(page_size))

        channel_video_convert_list = [
            {
                'id': chanel_video.id,
                'channel_id': chanel_video.channel_id,
                'channel_name': chanel_video.channel_name,
                'video_id': chanel_video.video_id,
                'title': chanel_video.title,
                'domain': chanel_video.domain,
                'url': chanel_video.url,
                'if_downloaded': chanel_video.if_downloaded,
                'uploaded_at': chanel_video.uploaded_at,
                'created_at': chanel_video.created_at
            } for chanel_video in channel_videos
        ]

        return {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "data": channel_video_convert_list
        }

    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


class DownloadChannelVideoRequest(BaseModel):
    channel_id: str
    video_id: str


@app.post("/api/channel/video/download")
def download_channel_video(req: DownloadChannelVideoRequest):
    try:
        channel_video = ChannelVideo.select().where(ChannelVideo.channel_id == req.channel_id,
                                                    ChannelVideo.video_id == req.video_id).first()
        download_service.start_download(channel_video.url)
        ChannelVideo.update(if_downloaded=True).where(ChannelVideo.channel_id == req.channel_id,
                                                      ChannelVideo.video_id == req.video_id).execute()
        return {"status": "success", "message": "下载任务已启动"}
    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


class DownloadTaskListRequest(BaseModel):
    page: str
    page_size: str


@app.get("/api/task/list")
def get_tasks(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    try:
        return get_updated_task_list(page, page_size)
    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


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


@app.get("/api/task/video/play/{task_id}")
async def play_video(task_id: str):
    try:
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

    except Exception as e:
        logger.error("视频播放错误", exc_info=True)
        raise HTTPException(status_code=500, detail="视频播放失败")
