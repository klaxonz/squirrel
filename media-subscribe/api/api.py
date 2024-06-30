import json
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.message_queue import RedisMessageQueue, Message
from common.constants import *
import service.download_service as download_service
from model.channel import Channel
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
