import json
import logging

from fastapi import Query, APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_

from common.constants import QUEUE_SUBSCRIBE_TASK
from common.message_queue import RedisMessageQueue
from common.database import get_session
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
    query: str = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    with get_session() as s:
        query_obj = s.query(Channel)

        if query:
            query_obj = query_obj.filter(
                or_(
                    Channel.name.ilike(f"%{query}%"),
                    Channel.url.ilike(f"%{query}%")
                )
            )

        total = query_obj.count()
        offset = (page - 1) * page_size
        channels = query_obj.order_by(Channel.created_at.desc()).offset(offset).limit(page_size)

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


class ToggleStatusRequest(BaseModel):
    channel_id: int
    if_enable: bool

@router.post("/api/channel/toggle-status")
def toggle_channel_status(req: ToggleStatusRequest):
    with get_session() as session:
        channel = session.query(Channel).filter(Channel.id == req.channel_id).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        channel.if_enable = req.if_enable
        session.commit()
    return response.success({"success": True})

@router.post("/api/channel/toggle-auto-download")
def toggle_auto_download(req: ToggleStatusRequest):
    with get_session() as session:
        channel = session.query(Channel).filter(Channel.id == req.channel_id).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        channel.if_auto_download = req.if_enable
        session.commit()
    return response.success({"success": True})

@router.post("/api/channel/toggle-download-all")
def toggle_download_all(req: ToggleStatusRequest):
    with get_session() as session:
        channel = session.query(Channel).filter(Channel.id == req.channel_id).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        channel.if_download_all = req.if_enable
        session.commit()
    return response.success({"success": True})

@router.post("/api/channel/toggle-extract-all")
def toggle_extract_all(req: ToggleStatusRequest):
    with get_session() as session:
        channel = session.query(Channel).filter(Channel.id == req.channel_id).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        channel.if_extract_all = req.if_enable
        session.commit()
    return response.success({"success": True})