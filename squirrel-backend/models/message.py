import datetime
from typing import Optional

from sqlalchemy import Text, Column, DateTime, Integer, VARCHAR
from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    __tablename__ = 'message'

    id: Optional[int] = Field(sa_column=Column(Integer, primary_key=True))
    body: str = Field(sa_column=Column(Text, nullable=False))
    send_status: str = Field(sa_column=Column(VARCHAR(32), nullable=False, default='PENDING'))
    retry_count: int = Field(default=0)
    next_retry_time: Optional[datetime.datetime] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now))
    updated_at: Optional[datetime.datetime] = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now,
                         index=True))
