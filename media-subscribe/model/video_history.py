from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlmodel import Field, SQLModel

class VideoHistory(SQLModel, table=True):
    __tablename__ = "video_history"
    
    id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=True))
    video_id: str = Field(sa_column=Column(String(255), nullable=False))
    channel_id: str = Field(sa_column=Column(String(255), nullable=False))
    watch_duration: int = Field(sa_column=Column(Integer, default=0))  # 观看时长(秒)
    last_position: int = Field(sa_column=Column(Integer, default=0))   # 最后观看位置(秒)
    total_duration: int = Field(sa_column=Column(Integer, default=0))  # 视频总时长(秒)
    created_at: datetime = Field(sa_column=Column(DateTime, nullable=False, default=datetime.now))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    )

    # 添加索引以优化查询性能
    __table_args__ = (
        Index('idx_video_history_video', 'video_id'),
        Index('idx_video_history_updated', 'updated_at'),
    ) 