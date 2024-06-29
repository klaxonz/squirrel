import asyncio
import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette import status
from starlette.websockets import WebSocket

from common.message_queue import RedisMessageQueue, Message
from common.constants import *
import service.download_service as download_service
from model.download_task import DownloadTask
from utils import json_serialize

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


@app.websocket("/ws/tasks")
async def task_status(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            tasks = get_updated_task_list()
            await websocket.send_text(json.dumps(tasks, default=json_serialize.more))
            await asyncio.sleep(1)
    except Exception as e:
        logger.error("WebSocket通信异常", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal Error")
    finally:
        # 清理资源等操作
        pass


def get_updated_task_list():
    tasks = DownloadTask.select().where(DownloadTask.title != '').order_by(DownloadTask.created_at.desc()).limit(10)

    task_convert_list = []
    for task in tasks:
        task_convert_list.append({
            "id": task.task_id,
            "status": task.status,
            "title": task.title,
            "downloaded_size": task.downloaded_size if task.downloaded_size else 0,
            "total_size": task.total_size if task.total_size else 0,
            "speed": task.speed if task.speed else '未知',
            "eta": task.eta if task.eta else '未知',
            "percent": task.percent if task.percent else '未知',
            "error_message": task.error_message,
            "created_at": task.created_at,
        })

    return task_convert_list
