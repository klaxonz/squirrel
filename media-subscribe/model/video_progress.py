import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlmodel import Field, SQLModel

class VideoProgress(SQLModel, table=True):
    __tablename__ = "video_progress"
    
    id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=True))
    channel_id: str = Field(sa_column=Column(String(255), nullable=False))
    video_id: str = Field(sa_column=Column(String(255), nullable=False))
    progress: float = Field(sa_column=Column(Float, default=0))
    created_at: datetime.datetime = Field(sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now))
    updated_at: datetime.datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now,
                         index=True))
