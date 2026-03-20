"""
订阅更新领域模型
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
    sync_state_id: Optional[int] = None
    queue_token: Optional[str] = None


@dataclass
class SubscriptionUpdateResult:
    """订阅更新结果"""
    subscription_id: int
    success: bool
    videos_found: int
    videos_enqueued: int
    error_message: Optional[str] = None
    skipped_reason: Optional[str] = None
    cursor_payload: Optional[dict] = None
    latest_video_url: Optional[str] = None
    total_available: Optional[int] = None


@dataclass
class SubscriptionScheduleResult:
    """订阅调度结果"""
    subscription_id: int
    sync_state_id: Optional[int]
    status: str
    request_id: Optional[str] = None

