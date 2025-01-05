from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, JSON, VARCHAR, Text
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models.mixins.serializer import SerializerMixin


class Creator(Base, SerializerMixin):
    __tablename__ = "creator"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

