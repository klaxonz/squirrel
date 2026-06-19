from datetime import datetime

from sqlalchemy import VARCHAR, Boolean, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import SerializerMixin


class VideoThumbnailLocalIndex(Base, SerializerMixin):
    __tablename__ = 'video_thumbnail_local_index'

    __table_args__ = (
        Index('ux_video_thumbnail_local_index_video_id', 'video_id', unique=True),
        Index('ix_video_thumbnail_local_index_batch_exists', 'batch_name', 'exists'),
        Index('ix_video_thumbnail_local_index_exists_indexed', 'exists', 'indexed_at'),
        Index('ix_video_thumbnail_local_index_updated_at', 'updated_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_name: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    filename: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    exists: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
        nullable=False,
    )
