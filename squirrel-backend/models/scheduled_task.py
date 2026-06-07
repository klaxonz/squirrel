from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, TEXT, VARCHAR, Boolean, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class TaskType(StrEnum):
    """Task type enumeration"""

    SYSTEM = "system"      # System built-in task
    USER = "user"         # User-defined task
    PLUGIN = "plugin"     # Plugin extension task


class TaskStatus(StrEnum):
    """Task status enumeration"""

    ENABLED = "enabled"   # Enabled
    DISABLED = "disabled" # Disabled
    RUNNING = "running"   # Running
    ERROR = "error"       # Error state


class ScheduledTask(Base, SerializerMixin):
    """Scheduled task configuration model"""

    __tablename__ = "scheduled_task"
    __table_args__ = (
        Index("ix_scheduled_task_status_created", "status", "created_at"),
        Index("ix_scheduled_task_type_created", "task_type", "created_at"),
        Index("ix_scheduled_task_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, unique=True, comment="Task name")
    task_type: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default=TaskType.USER.value, comment="Task type")
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="Task description")

    # Execution configuration
    interval: Mapped[int] = mapped_column(Integer, nullable=False, default=60, comment="Execution interval value")
    unit: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default="seconds", comment="Time unit")
    start_immediately: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="Whether to execute immediately")
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="Max retry count")

    # Status control
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default=TaskStatus.ENABLED.value, comment="Task status")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="Whether active")

    # Task configuration
    task_class: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, comment="Task class name")
    task_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default={}, comment="Task parameters")

    # Execution info
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="Last run time")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="Next run time")
    last_error: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="Last error message")
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Run count")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Success count")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Error count")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    created_by: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True, comment="Creator")
    updated_by: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True, comment="Updater")


class TaskExecutionLog(Base, SerializerMixin):
    """Task execution log model"""

    __tablename__ = "task_execution_log"
    __table_args__ = (
        Index("ix_task_execution_log_started_at", "started_at"),
        Index("ix_task_execution_log_task_started", "task_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="Task ID")
    task_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, comment="Task name")

    # Execution info
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, comment="Start time")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="Finish time")
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Duration (ms)")
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, comment="Execution status")

    # Execution result
    error_message: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="Error message")
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="Execution result data")

    # Metadata
    executed_by: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True, comment="Executor")
    trace_id: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True, comment="Trace ID")
