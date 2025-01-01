from datetime import datetime
from typing import Optional

from sqlalchemy import Text, DateTime, Integer, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class Message(Base):
    __tablename__ = 'message'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    send_status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default='PENDING')
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )
