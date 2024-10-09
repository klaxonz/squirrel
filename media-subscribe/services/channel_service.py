import json
from typing import List, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from common import constants
from core.cache import RedisClient
from core.message_queue import RedisMessageQueue
from model.channel import Channel, ChannelVideo
from model.message import Message


class ChannelService:
    def __init__(self, db: Session):
        self.db = db

    def get_subscription_status(self, channel_id: str) -> bool:
        channel = self.db.query(Channel).filter(Channel.channel_id == channel_id).first()
        return channel is not None

    def subscribe_channel(self, url: str):
        subscribe_queue = RedisMessageQueue(queue_name=constants.QUEUE_SUBSCRIBE_TASK)
        task = {"url": url}
        message = Message(body=json.dumps(task))
        self.db.add(message)
        self.db.commit()
        subscribe_queue.enqueue(message)
        self.db.query(Message).filter(Message.message_id == message.message_id).update({"send_status": "SENDING"})

    def update_channel(self, channel_id: int, data: dict):
        self.db.query(Channel).filter(Channel.id == channel_id).update(data)
        self.db.commit()

    def delete_channel(self, channel_id: int):
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            self.db.delete(channel)
            self.db.query(ChannelVideo).filter(ChannelVideo.channel_id == channel.channel_id).delete()
            self.db.commit()

    def get_channel_detail(self, channel_id: int):
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            return {
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
        return None

    def list_channels(self, query: str, page: int, page_size: int) -> Tuple[List[dict], int]:
        query_obj = self.db.query(Channel)
        if query:
            query_obj = query_obj.filter(or_(Channel.name.ilike(f"%{query}%"), Channel.url.ilike(f"%{query}%")))
        total = query_obj.count()
        offset = (page - 1) * page_size
        channels = query_obj.order_by(Channel.created_at.desc()).offset(offset).limit(page_size)
        channel_list = [{
            'id': channel.id,
            'channel_id': channel.channel_id,
            'name': channel.name,
            'url': channel.url,
            'avatar': channel.avatar,
            'total_videos': channel.total_videos,
            'total_extract': self.count_channel_videos(channel.channel_id),
            'if_enable': channel.if_enable,
            'if_auto_download': channel.if_auto_download,
            'if_download_all': channel.if_download_all,
            'if_extract_all': channel.if_extract_all,
            'created_at': channel.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for channel in channels]
        return channel_list, total

    def count_channel_videos(self, channel_id: str) -> int:
        return self.db.query(ChannelVideo).filter(ChannelVideo.channel_id == channel_id).count()

    def toggle_channel_status(self, channel_id: int, status: bool, field: str):
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            setattr(channel, field, status)
            self.db.commit()
            return True
        return False

    def unsubscribe_channel(self, channel_id: int):
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            self.db.query(ChannelVideo).filter(ChannelVideo.channel_id == channel.channel_id).delete()
            self.db.delete(channel)
            self.db.commit()
            redis_client = RedisClient.get_instance().client
            redis_client.sadd(constants.UNSUBSCRIBED_CHANNELS_SET, channel.channel_id)
            redis_client.expire(constants.UNSUBSCRIBED_CHANNELS_SET, constants.UNSUBSCRIBE_EXPIRATION)
            return True
        return False
