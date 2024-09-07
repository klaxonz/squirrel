from datetime import datetime

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import Column, Boolean, DateTime, Integer
from sqlalchemy.dialects.mysql import VARCHAR

from common.database import Base, BaseMixin


class Channel(Base, BaseMixin):
    __tablename__ = 'channel'

    id = Column(Integer, primary_key=True)
    channel_id = Column(VARCHAR(255), nullable=False)
    name = Column(VARCHAR(255), nullable=False)
    url = Column(VARCHAR(1024), nullable=False)
    avatar = Column(VARCHAR(2048), nullable=False)
    total_videos = Column(Integer, nullable=False, default=0)
    if_enable = Column(Boolean, default=True)
    if_auto_download = Column(Boolean, default=False)
    if_download_all = Column(Boolean, default=False)
    if_extract_all = Column(Boolean, default=False)


class ChannelVideo(Base, BaseMixin):
    __tablename__ = 'channel_video'

    id = Column(Integer, primary_key=True)
    channel_id = Column(VARCHAR(255), nullable=False)
    channel_name = Column(VARCHAR(255), nullable=False)
    channel_avatar = Column(VARCHAR(2048), nullable=False)
    title = Column(VARCHAR(255), nullable=True)
    video_id = Column(VARCHAR(64), nullable=False)
    domain = Column(VARCHAR(255), nullable=False)
    url = Column(VARCHAR(1024), nullable=False)
    thumbnail = Column(VARCHAR(2048), nullable=True)
    duration = Column(Integer, nullable=True)
    if_read = Column(Boolean, default=False)
    if_downloaded = Column(Boolean, default=False)
    is_disliked = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, nullable=True, default=datetime.now)


class ChannelVideoSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ChannelVideo
        load_instance = True
