from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, VARCHAR, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from models import Base
from models.mixins.serializer import SerializerMixin


class VipVideoRecord(Base, SerializerMixin):
    __tablename__ = "vip_video_record"

    __table_args__ = (
        Index('ix_vip_video_url', 'url'),
        Index('ix_vip_video_site', 'site'),
        Index('ix_vip_video_created_at', 'created_at'),
        Index('ux_vip_video_url_unique', 'url', unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    site: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )
