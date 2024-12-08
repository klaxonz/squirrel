import json
from typing import List, Tuple

from sqlalchemy import or_, func
from sqlmodel import select, col, delete

from common import constants
from core.cache import RedisClient
from core.database import get_session
from model.channel import Channel, ChannelVideo
from model.message import Message
from consumer import subscribe_task


class ChannelService:
    def __init__(self):
        pass


    def get_channel(self, channel_id: str):
        with get_session() as session:
            channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
            return channel


    def get_subscription_status(self, channel_url: str) -> bool:
        with get_session() as session:
            channel = session.exec(select(Channel).where(Channel.url == channel_url)).first()
            return channel is not None

    def subscribe_channel(self, url: str):
        with get_session() as session:
            task = {"url": url}
            message = Message(
                body=json.dumps(task),
            )
            session.add(message)
            session.commit()

            message = session.exec(select(Message).where(Message.message_id == message.message_id)).first()
            dump_json = message.model_dump_json()
            subscribe_task.process_subscribe_message.send(dump_json)
            message.send_status = 'SENDING'
            session.refresh(message)

    def update_channel(self, channel_id: int, data: dict):
        with get_session() as session:
            session.exec(select(Channel).where(Channel.id == channel_id).update(data))
            session.commit()

    def delete_channel(self, channel_id: int):
        with get_session() as session:
            channel = session.query(Channel).filter(Channel.id == channel_id).first()
            if channel:
                session.delete(channel)
                session.query(ChannelVideo).filter(ChannelVideo.channel_id == channel.channel_id).delete()
                session.commit()

    def get_channel_detail(self, channel_id: int):
        with get_session() as session:
            channel = session.query(Channel).filter(Channel.id == channel_id).first()
            if channel:
                return {
                    "id": channel.id,
                    "channel_id": channel.channel_id,
                    "name": channel.name,
                    "url": channel.url,
                    "total": channel.total_videos,
                    "if_enable": channel.if_enable,
                    "if_auto_download": channel.if_auto_download,
                    "if_download_all": channel.if_download_all,
                    "if_extract_all": channel.if_extract_all,
                    "created_at": channel.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
            return None

    def list_channels(self, query: str, page: int, page_size: int) -> Tuple[List[dict], int]:
        with get_session() as session:
            query_obj = session.query(Channel)
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
        with get_session() as session:
            return session.exec(select(func.count(ChannelVideo.id))
            .where(
                or_(
                    ChannelVideo.channel_id == channel_id,
                    col(ChannelVideo.channel_id).like(f"{channel_id},%"),
                    col(ChannelVideo.channel_id).like(f"%,{channel_id}"),
                    col(ChannelVideo.channel_id).like(f"%,{channel_id},%")
                )
               )).one()


    def toggle_channel_status(self, channel_id: int, status: bool, field: str):
        with get_session() as session:
            channel = session.query(Channel).filter(Channel.id == channel_id).first()
            if channel:
                setattr(channel, field, status)
                session.commit()
                return True
            return False

    def unsubscribe_channel(self, channel_id: int, channel_url: str):
        with get_session() as session:
            if channel_id or channel_url:
                channel = None
                if channel_id:
                    channel = session.exec(select(Channel).where(Channel.id == channel_id)).first()
                if channel_url and  channel is None:
                    channel = session.exec(select(Channel).where(Channel.url == channel_url)).first()
                if channel:
                    session.delete(channel)
                    session.exec(delete(ChannelVideo).where(ChannelVideo.channel_id == channel.channel_id))
                    session.commit()
                    redis_client = RedisClient.get_instance().client
                    redis_client.sadd(constants.UNSUBSCRIBED_CHANNELS_SET, channel.channel_id)
                    redis_client.expire(constants.UNSUBSCRIBED_CHANNELS_SET, constants.UNSUBSCRIBE_EXPIRATION)
                    return True
            return False
