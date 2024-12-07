import datetime

from sqlalchemy import Column, Boolean, DateTime, Integer, Index
from sqlalchemy.dialects.mysql import VARCHAR
from sqlmodel import Field, SQLModel


class Channel(SQLModel, table=True):
    __tablename__ = 'channel'
    
    __table_args__ = (
        Index('idx_channel_name', 'name'),
    )

    id: int = Field(sa_column=Column(Integer, primary_key=True))
    channel_id: str = Field(sa_column=Column(VARCHAR(255), nullable=False, index=True))
    name: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    url: str = Field(sa_column=Column(VARCHAR(1024), nullable=False))
    avatar: str = Field(sa_column=Column(VARCHAR(2048), nullable=False))
    total_videos: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    if_enable: bool = Field(sa_column=Column(Boolean, default=True))
    if_auto_download: bool = Field(sa_column=Column(Boolean, default=False))
    if_download_all: bool = Field(sa_column=Column(Boolean, default=False))
    if_extract_all: bool = Field(sa_column=Column(Boolean, default=False))
    created_at: datetime.datetime = Field(sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now, index=True))
    updated_at: datetime.datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now,
                         index=True))


class ChannelVideo(SQLModel, table=True):
    __tablename__ = 'channel_video'
    
    # 添加复合索引
    __table_args__ = (
        Index('idx_channel_video_channel_uploaded', 'channel_id', 'uploaded_at'),
        Index('idx_channel_video_read_status', 'channel_id', 'if_read'),
    )

    id: int = Field(sa_column=Column(Integer, primary_key=True))
    channel_id: str = Field(sa_column=Column(VARCHAR(255), nullable=False, index=True))
    channel_name: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    channel_avatar: str = Field(sa_column=Column(VARCHAR(2048), nullable=False))
    title: str = Field(sa_column=Column(VARCHAR(1024), nullable=True))
    video_id: str = Field(sa_column=Column(VARCHAR(64), nullable=False, index=True))
    domain: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    url: str = Field(sa_column=Column(VARCHAR(1024), nullable=False))
    thumbnail: str = Field(sa_column=Column(VARCHAR(2048), nullable=True))
    duration: int = Field(sa_column=Column(Integer, nullable=True))
    if_read: bool = Field(sa_column=Column(Boolean, default=False))
    if_downloaded: bool = Field(sa_column=Column(Boolean, default=False))
    is_liked: bool = Field(sa_column=Column(Integer, nullable=True))
    uploaded_at: datetime.datetime = Field(sa_column=Column(DateTime, nullable=True, default=datetime.datetime.now, index=True))  # 添加索引
    created_at: datetime.datetime = Field(sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now))
    updated_at: datetime.datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now,
                         index=True))
