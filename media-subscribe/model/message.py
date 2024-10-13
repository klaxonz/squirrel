from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import Text, String, func, Index


class Message(SQLModel, table=True):
    __tablename__ = 'message'

    message_id: Optional[int] = Field(default=None, primary_key=True)
    body: str = Field(...)
    send_status: str = Field(default='PENDING')
    retry_count: int = Field(default=0)
    next_retry_time: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        sa_column_kwargs = {
            "message_id": {"autoincrement": True},
            "body": {"type": Text()},
            "send_status": {"type": String(32)},
            "created_at": {"server_default": func.current_timestamp()},
            "updated_at": {"server_default": func.current_timestamp(), "onupdate": func.current_timestamp()}
        }

    __table_args__ = (
        Index('ix_message_updated_at', 'updated_at'),
    )
