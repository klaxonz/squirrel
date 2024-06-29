import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from common.message_queue import RedisMessageQueue, Message
from common.constants import *
import uuid
import service.download_service as download_service
from model.task import Task

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

        task_id = str(uuid.uuid4()).replace('-', '')
        task = {
            "url": req.url,
            "task_id": task_id,
            "task_type": MESSAGE_TYPE_SUBSCRIBE,
        }

        Task.create_task(task)
        message = Message(task, task_id, MESSAGE_TYPE_SUBSCRIBE)
        subscribe_queue.enqueue(message)

        return {"status": "success", "message": "订阅成功"}
    except Exception as e:
        logger.error("订阅失败", exc_info=True)
        raise HTTPException(status_code=500, detail="订阅失败")


@app.post("/api/task/list")
def subscribe_channel():
    try:
        pass
    except Exception as e:
        logger.error("订阅失败", exc_info=True)
        raise HTTPException(status_code=500, detail="订阅失败")