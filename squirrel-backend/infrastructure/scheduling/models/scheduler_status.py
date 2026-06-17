from datetime import datetime

from sqlalchemy import TEXT, VARCHAR, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import SerializerMixin


class SchedulerStatus(Base, SerializerMixin):
    """Scheduler status model (for cross-process state sharing)"""

    __tablename__ = "scheduler_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_name: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True, comment="Process name")
    is_running: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="Whether running")
    job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Job count")
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, comment="Last heartbeat time")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="Start time")
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="Stop time")
    error_message: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="Error message")
