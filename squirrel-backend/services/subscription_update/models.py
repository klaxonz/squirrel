"""
订阅更新领域模型
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class UpdateTrigger(Enum):
    """更新触发方式"""
    SCHEDULED = "scheduled"  # 定时自动
    MANUAL = "manual"        # 手动刷新
    API = "api"              # API触发


class UpdateMode(Enum):
    """更新模式"""
    INCREMENTAL = "incremental"  # 增量更新
    FULL = "full"                # 全量更新
    SMART = "smart"              # 智能判断


@dataclass
class SubscriptionUpdateRequest:
    """订阅更新请求"""
    subscription_id: int
    url: str
    trigger: UpdateTrigger
    mode: UpdateMode = UpdateMode.SMART
    user_id: Optional[int] = None
    force: bool = False
    trace_id: Optional[str] = None


@dataclass
class SubscriptionUpdateResult:
    """订阅更新结果"""
    subscription_id: int
    success: bool
    videos_found: int
    videos_enqueued: int
    error_message: Optional[str] = None
    skipped_reason: Optional[str] = None

