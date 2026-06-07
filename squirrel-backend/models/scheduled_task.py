from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, TEXT, VARCHAR, Boolean, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class TaskType(StrEnum):
    """任务类型枚举"""

    SYSTEM = "system"      # 系统内置任务
    USER = "user"         # 用户自定义任务
    PLUGIN = "plugin"     # 插件扩展任务


class TaskStatus(StrEnum):
    """任务状态枚举"""

    ENABLED = "enabled"   # 启用
    DISABLED = "disabled" # 禁用
    RUNNING = "running"   # 正在运行
    ERROR = "error"       # 错误状态


class ScheduledTask(Base, SerializerMixin):
    """定时任务配置模型"""

    __tablename__ = "scheduled_task"
    __table_args__ = (
        Index("ix_scheduled_task_status_created", "status", "created_at"),
        Index("ix_scheduled_task_type_created", "task_type", "created_at"),
        Index("ix_scheduled_task_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, unique=True, comment="任务名称")
    task_type: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default=TaskType.USER.value, comment="任务类型")
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="任务描述")

    # 执行配置
    interval: Mapped[int] = mapped_column(Integer, nullable=False, default=60, comment="执行间隔数值")
    unit: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default="seconds", comment="时间单位")
    start_immediately: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否立即执行")
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="最大重试次数")

    # 状态控制
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default=TaskStatus.ENABLED.value, comment="任务状态")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否激活")

    # 任务配置
    task_class: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, comment="任务类名")
    task_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default={}, comment="任务参数")

    # 执行信息
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后执行时间")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="下次执行时间")
    last_error: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="最后错误信息")
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="执行次数")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="成功次数")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="失败次数")

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    created_by: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True, comment="创建者")
    updated_by: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True, comment="更新者")


class TaskExecutionLog(Base, SerializerMixin):
    """任务执行日志模型"""

    __tablename__ = "task_execution_log"
    __table_args__ = (
        Index("ix_task_execution_log_started_at", "started_at"),
        Index("ix_task_execution_log_task_started", "task_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="任务ID")
    task_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, comment="任务名称")

    # 执行信息
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="完成时间")
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="执行时长(毫秒)")
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, comment="执行状态")

    # 执行结果
    error_message: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="错误信息")
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="执行结果数据")

    # 元数据
    executed_by: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True, comment="执行者")
    trace_id: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True, comment="链路追踪ID")
