from datetime import datetime

from sqlalchemy import VARCHAR, DateTime, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import SerializerMixin


class SystemConfig(Base, SerializerMixin):
    __tablename__ = "system_config"
    __table_args__ = (
        UniqueConstraint("key", name="uq_system_config_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 配置键（如 enable_scheduler / enable_worker）
    key: Mapped[str] = mapped_column(VARCHAR(191), nullable=False)
    # 配置值（字符串化存储，如 "true"/"false" 或其他文本）
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 创建与更新时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
