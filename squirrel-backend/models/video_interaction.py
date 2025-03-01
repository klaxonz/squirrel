from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from models import Base
from models.mixins.serializer import SerializerMixin


class VideoInteraction(Base, SerializerMixin):
    __tablename__ = 'video_interaction' 

    __table_args__ = (
        Index('ix_video_interaction_user_video', 'user_id', 'video_id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    interaction_type: Mapped[int] = mapped_column(Integer, nullable=False, comment="1: like, 2: dislike")
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

