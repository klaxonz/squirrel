import json
import logging

from fastapi import Query, APIRouter
from pydantic import BaseModel

from common.constants import QUEUE_SUBSCRIBE_TASK
from common.message_queue import RedisMessageQueue
from model.channel import Channel
from model.message import Message
import common.response as response

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=['频道接口']
)


class SubscribeChannelRequest(BaseModel):
    url: str


@router.post("/api/channel/subscribe")
def subscribe_channel(req: SubscribeChannelRequest):
    subscribe_queue = RedisMessageQueue(queue_name=QUEUE_SUBSCRIBE_TASK)
    task = {
        "url": req.url,
    }
    message = Message(body=json.dumps(task))
    message.save()

    subscribe_queue.enqueue(message)
    Message.update(send_status='SENDING').where(Message.message_id == message.message_id).execute()

    return response.success()


class ChannelUpdateRequest(BaseModel):
    id: int
    ifEnable: bool
    ifAutoDownload: bool
    ifDownloadAll: bool


@router.post("/api/channel/update")
def update_chanel(req: ChannelUpdateRequest):
    Channel.update(if_enable=req.ifEnable, if_auto_download=req.ifAutoDownload, if_download_all=req.ifDownloadAll).where(
        Channel.id == req.id).execute()
    return response.success()


@router.get("/api/channel/detail")
def channel_detail(id: int):
    channel = Channel.select().where(Channel.id == id).get()

    channel_dict = {
        "id": channel.id,
        "channelId": channel.channel_id,
        "name": channel.name,
        "url": channel.url,
        "ifEnable": channel.if_enable,
        "ifAutoDownload": channel.if_auto_download,
        "ifDownloadAll": channel.if_download_all,
        "createdAt": channel.created_at,
    }

    return response.success(channel_dict)


@router.get("/api/channel/list")
def subscribe_channel(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
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
            'if_download_all': channel.if_download_all,
            'created_at': channel.created_at
        } for channel in channels
    ]

    channel_list = {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "data": channel_convert_list
    }
    return response.success(channel_list)

