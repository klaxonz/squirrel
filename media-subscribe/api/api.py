import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from common.message_queue import RedisMessageQueue, Message
from model.task import Task
from common.constants import *
import uuid

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
        task_id = str(uuid.uuid4()).replace('-', '')
        task = {
            "url": req.url,
            "task_id": task_id,
            "task_type": MESSAGE_TYPE_DOWNLOAD,
        }

        Task.create_task(task)
        message = Message(task, task_id)
        RedisMessageQueue(queue_name=QUEUE_DOWNLOAD_TASK).enqueue(message)

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

        message_id = str(uuid.uuid4()).replace('-', '')
        message_content = {
            "url": req.url
        }
        message = Message(message_content, message_id, MESSAGE_TYPE_SUBSCRIBE)
        subscribe_queue.enqueue(message)

        # 获取到频道信息

        # 频道信息入库

        # 配置定时任务，自动拉取每个频道前 n 条数据

        # 可以全局配置，也可以单个channel配置，channel配置优先级高于全局配置

        return {"status": "success", "message": "订阅成功"}
    except Exception as e:
        print(f"订阅失败: ", e)
        raise HTTPException(status_code=500, detail="订阅失败")
