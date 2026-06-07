"""订阅更新领域模型
"""
from dataclasses import dataclass
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
    user_id: int | None = None
    force: bool = False
    trace_id: str | None = None
    request_id: str | None = None
    run_id: str | None = None
    sync_state_id: int | None = None
    queue_token: str | None = None
    cursor_payload: dict | None = None
    last_seen_video_url: str | None = None
    inline_video_extraction: bool = False


@dataclass
class SubscriptionUpdateResult:
    """订阅更新结果"""

    subscription_id: int
    success: bool
    videos_found: int
    videos_enqueued: int
    has_more: bool = False
    error_message: str | None = None
    skipped_reason: str | None = None
    cursor_payload: dict | None = None
    latest_video_url: str | None = None
    source_video_count: int | None = None
    total_available: int | None = None
    head_sample_urls: list[str] | None = None
    anchor_found: bool | None = None
    oldest_scanned_url: str | None = None
    cursor_invalid: bool | None = None
    cursor_loop_detected: bool | None = None
    scan_depth: int | None = None


@dataclass
class SubscriptionScheduleResult:
    """订阅调度结果"""

    subscription_id: int
    sync_state_id: int | None
    status: str
    request_id: str | None = None
    run_id: str | None = None


@dataclass
class SubscriptionDirectRunResult:
    """订阅直接执行结果"""

    subscription_id: int
    sync_state_id: int | None
    status: str
    request_id: str | None = None
    run_id: str | None = None
    result: SubscriptionUpdateResult | None = None

