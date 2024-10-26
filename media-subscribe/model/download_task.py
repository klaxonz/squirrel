import datetime
from typing import Optional

from sqlalchemy import Column, BigInteger, Text, Integer, DateTime
from sqlalchemy.dialects.mysql import VARCHAR
from sqlmodel import Field, SQLModel


class DownloadTask(SQLModel, table=True):
    __tablename__ = 'download_task'

    task_id: Optional[int] = Field(sa_column=Column(Integer, primary_key=True))
    url: str = Field(sa_column=Column(VARCHAR(2048), nullable=False))
    thumbnail: Optional[str] = Field(sa_column=Column(VARCHAR(2048), nullable=True))
    domain: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    video_id: str = Field(sa_column=Column(VARCHAR(64), nullable=False))
    channel_id: Optional[str] = Field(sa_column=Column(VARCHAR(255), nullable=True))
    channel_name: Optional[str] = Field(sa_column=Column(VARCHAR(255), nullable=True))
    channel_url: Optional[str] = Field(sa_column=Column(VARCHAR(2048), nullable=True))
    channel_avatar: Optional[str] = Field(sa_column=Column(VARCHAR(2048), nullable=True))
    title: Optional[str] = Field(sa_column=Column(VARCHAR(255), nullable=True))
    status: str = Field(sa_column=Column(VARCHAR(32), nullable=False, default='PENDING'))
    downloaded_size: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True, default=0))
    total_size: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True, default=0))
    speed: Optional[str] = Field(sa_column=Column(VARCHAR(255), nullable=True))
    eta: Optional[str] = Field(sa_column=Column(VARCHAR(32), nullable=True))
    percent: Optional[str] = Field(sa_column=Column(VARCHAR(32), nullable=True))
    retry: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    error_message: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    created_at: Optional[datetime.datetime] = Field(sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now))
    updated_at: Optional[datetime.datetime] = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now,
                         index=True))
