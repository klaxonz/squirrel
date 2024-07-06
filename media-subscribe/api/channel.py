import json
import logging

from fastapi import HTTPException, Query, APIRouter
from pydantic import BaseModel

from common.constants import QUEUE_SUBSCRIBE_TASK
from common.message_queue import RedisMessageQueue
from model.channel import Channel
from model.message import Message

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=['频道接口']
)


class SubscribeChannelRequest(BaseModel):
    url: str


@router.post("/api/channel/subscribe")
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


class ChannelUpdateRequest(BaseModel):
    id: int
    ifEnable: bool
    ifAutoDownload: bool


@router.post("/api/channel/update")
def update_chanel(req: ChannelUpdateRequest):
    try:
        Channel.update(if_enable=req.ifEnable, if_auto_download=req.ifAutoDownload).where(
            Channel.id == req.id).execute()
        return {"status": "success", "message": "更新成功"}
    except Exception as e:
        logger.error("订阅失败", exc_info=True)
        raise HTTPException(status_code=500, detail="订阅失败")


@router.get("/api/channel/detail")
def channel_detail(id: int):
    try:
        channel = Channel.select().where(Channel.id == id).get()
        return {
            "id": channel.id,
            "channelId": channel.channel_id,
            "name": channel.name,
            "url": channel.url,
            "ifEnable": channel.if_enable,
            "ifAutoDownload": channel.if_auto_download,
            "createdAt": channel.created_at,
        }
    except Exception as e:
        logger.error("订阅失败", exc_info=True)
        raise HTTPException(status_code=500, detail="订阅失败")


@router.get("/api/channel/list")
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
                'if_auto_download': channel.if_auto_download,
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
