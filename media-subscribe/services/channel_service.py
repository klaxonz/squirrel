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

    def get_subscription_status(self, channel_id: str) -> bool:
        with get_session() as session:
            channel = session.exec(select(Channel).where(Channel.channel_id == channel_id)).first()
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
            # 基础查询
            query_obj = session.query(Channel)
            if query:
                query_obj = query_obj.filter(or_(Channel.name.ilike(f"%{query}%"), Channel.url.ilike(f"%{query}%")))
            
            # 获取总数
            total = query_obj.count()
            
            # 分页获取频道
            offset = (page - 1) * page_size
            channels = query_obj.order_by(Channel.created_at.desc()).offset(offset).limit(page_size).all()
            
            # 获取所有频道ID
            channel_ids = [channel.channel_id for channel in channels]
            
            # 一次性查询所有频道的视频数量
            video_counts = {}
            if channel_ids:
                counts_query = session.query(
                    ChannelVideo.channel_id,
                    func.count(ChannelVideo.id).label('count')
                ).filter(
                    or_(
                        ChannelVideo.channel_id.in_(channel_ids),
                        *[
                            or_(
                                ChannelVideo.channel_id.like(f"{cid},%"),
                                ChannelVideo.channel_id.like(f"%,{cid}"),
                                ChannelVideo.channel_id.like(f"%,{cid},%")
                            ) for cid in channel_ids
                        ]
                    )
                ).group_by(ChannelVideo.channel_id).all()
                
                # 将结果转换为字典
                for channel_id, count in counts_query:
                    video_counts[channel_id] = count
            
            # 构建返回结果
            channel_list = [{
                'id': channel.id,
                'channel_id': channel.channel_id,
                'name': channel.name,
                'url': channel.url,
                'avatar': channel.avatar,
                'total_videos': channel.total_videos,
                'total_extract': video_counts.get(channel.channel_id, 0),  # 使用预先查询的结果
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

    def unsubscribe_channel(self, channel_id: int):
        with get_session() as session:
            channel = session.exec(select(Channel).where(Channel.id == channel_id)).first()
            if channel:
                session.delete(channel)
                session.exec(delete(ChannelVideo).where(ChannelVideo.channel_id == channel.channel_id))
                session.commit()
                redis_client = RedisClient.get_instance().client
                redis_client.sadd(constants.UNSUBSCRIBED_CHANNELS_SET, channel.channel_id)
                redis_client.expire(constants.UNSUBSCRIBED_CHANNELS_SET, constants.UNSUBSCRIBE_EXPIRATION)
                return True
            return False
