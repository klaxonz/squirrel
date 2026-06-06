from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, DateTime, Boolean, VARCHAR, TEXT
from sqlalchemy.orm import mapped_column, Mapped
from models import Base
from models.mixins.serializer import SerializerMixin


class SchedulerStatus(Base, SerializerMixin):
    """调度器状态模型（用于跨进程状态共享）"""
    __tablename__ = 'scheduler_status'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_name: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True, comment="进程名称")
    is_running: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否运行中")
    job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="任务数量")
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, comment="最后心跳时间")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="启动时间")
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="停止时间")
    error_message: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True, comment="错误信息")
