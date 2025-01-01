from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Integer, Text
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class DownloadTask(Base):
    __tablename__ = 'download_task'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default='PENDING')
    downloaded_size: Mapped[int] = mapped_column(BigInteger, nullable=True, default=0)
    total_size: Mapped[int] = mapped_column(BigInteger, nullable=True, default=0)
    speed: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    eta: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    percent: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    retry: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

