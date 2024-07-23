import json
import logging

from fastapi import Query, APIRouter
from pydantic import BaseModel

from common.constants import QUEUE_SUBSCRIBE_TASK
from common.database import get_session
from common.message_queue import RedisMessageQueue
from model.channel import Channel, ChannelVideo
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

    with get_session() as s:
        message = Message()
        message.body = json.dumps(task)
        s.add(message)
        s.commit()

        subscribe_queue.enqueue(message)

        s.query(Message).filter(Message.message_id == message.message_id).update({"send_status": "SENDING"})

        return response.success()


class ChannelUpdateRequest(BaseModel):
    id: int
    if_enable: bool
    if_auto_download: bool
    if_download_all: bool
    if_extract_all: bool


@router.post("/api/channel/update")
def update_chanel(req: ChannelUpdateRequest):
    with get_session() as s:
        s.query(Channel).filter(Channel.id == req.id).update(
            {"if_enable": req.if_enable, "if_auto_download": req.if_auto_download,
             "if_download_all": req.if_download_all, "if_extract_all": req.if_extract_all})

    return response.success()


class ChannelDeleteRequest(BaseModel):
    id: int


@router.post("/api/channel/delete")
def delete_channel(req: ChannelDeleteRequest):
    with get_session() as s:
        channel = s.query(Channel).filter(Channel.id == req.id).first()
        if channel:
            s.delete(channel)
            s.query(ChannelVideo).filter(ChannelVideo.channel_id == channel.channel_id).delete()
            s.commit()
    return response.success()


@router.get("/api/channel/detail")
def channel_detail(id: int):
    with get_session() as s:
        channel = s.query(Channel).filter(Channel.id == id).first()

        channel_dict = {
            "id": channel.id,
            "channel_id": channel.channel_id,
            "name": channel.name,
            "url": channel.url,
            "if_enable": channel.if_enable,
            "if_auto_download": channel.if_auto_download,
            "if_download_all": channel.if_download_all,
            "if_extract_all": channel.if_extract_all,
            "created_at": channel.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }

        return response.success(channel_dict)


@router.get("/api/channel/list")
def subscribe_channel(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    with get_session() as s:
        total = s.query(Channel).count()
        offset = (page - 1) * page_size
        channels = (s.query(Channel).order_by(Channel.created_at.desc()).offset(offset).limit(page_size))
        channel_convert_list = [
            {
                'id': channel.id,
                'channel_id': channel.channel_id,
                'name': channel.name,
                'url': channel.url,
                'avatar': channel.avatar,
                'total_videos': channel.total_videos,
                'total_extract': count_channel_videos(channel.channel_id),
                'if_enable': channel.if_enable,
                'if_auto_download': channel.if_auto_download,
                'if_download_all': channel.if_download_all,
                'if_extract_all': channel.if_extract_all,
                'created_at': channel.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for channel in channels
        ]

        channel_list = {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "data": channel_convert_list
        }

    return response.success(channel_list)


def count_channel_videos(channel_id):
    with get_session() as s:
        return s.query(ChannelVideo).filter(ChannelVideo.channel_id == channel_id).count()
