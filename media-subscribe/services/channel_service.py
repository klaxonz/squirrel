import json
from typing import List, Tuple

from mutagen.dsdiff import delete
from sqlalchemy import or_, func
from sqlmodel import Session, select, col

from common import constants
from core.cache import RedisClient
from model.channel import Channel, ChannelVideo
from model.message import Message
from consumer import subscribe_task


class ChannelService:
    def __init__(self, session: Session):
        self.session = session

    def get_subscription_status(self, channel_id: str) -> bool:
        channel = self.session.exec(select(Channel).where(Channel.channel_id == channel_id)).first()
        return channel is not None

    def subscribe_channel(self, url: str):
        task = {"url": url}
        message = Message(
            body=json.dumps(task),
        )
        self.session.add(message)
        self.session.commit()

        message = self.session.exec(select(Message).where(Message.message_id == message.message_id)).first()
        dump_json = message.model_dump_json()
        subscribe_task.process_subscribe_message.send(dump_json)
        message.send_status = 'SENDING'
        self.session.refresh(message)

    def update_channel(self, channel_id: int, data: dict):
        self.session.exec(select(Channel).where(Channel.id == channel_id).update(data))
        self.session.commit()

    def delete_channel(self, channel_id: int):
        channel = self.session.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            self.session.delete(channel)
            self.session.query(ChannelVideo).filter(ChannelVideo.channel_id == channel.channel_id).delete()
            self.session.commit()

    def get_channel_detail(self, channel_id: int):
        channel = self.session.query(Channel).filter(Channel.id == channel_id).first()
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
        query_obj = self.session.query(Channel)
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
        return self.session.exec(select(func.count(ChannelVideo.id))
        .where(
            or_(
                ChannelVideo.channel_id == channel_id,
                col(ChannelVideo.channel_id).like(f"{channel_id},%"),
                col(ChannelVideo.channel_id).like(f"%,{channel_id}"),
                col(ChannelVideo.channel_id).like(f"%,{channel_id},%")
            )
           )).one()

    def toggle_channel_status(self, channel_id: int, status: bool, field: str):
        channel = self.session.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            setattr(channel, field, status)
            self.session.commit()
            return True
        return False

    def unsubscribe_channel(self, channel_id: int):
        channel = self.session.exec(select(Channel).where(Channel.id == channel_id)).first()
        if channel:
            self.session.exec(delete(ChannelVideo).where(ChannelVideo.channel_id == channel.channel_id))
            self.session.commit()
            redis_client = RedisClient.get_instance().client
            redis_client.sadd(constants.UNSUBSCRIBED_CHANNELS_SET, channel.channel_id)
            redis_client.expire(constants.UNSUBSCRIBED_CHANNELS_SET, constants.UNSUBSCRIBE_EXPIRATION)
            return True
        return False
