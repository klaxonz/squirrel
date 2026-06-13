"""Subscription update domain models
"""
from dataclasses import dataclass
from enum import Enum


class UpdateTrigger(Enum):
    """Update trigger type"""

    SCHEDULED = "scheduled"  # Scheduled automatic
    MANUAL = "manual"        # Manual refresh
    API = "api"              # API triggered


class UpdateMode(Enum):
    """Update mode"""

    INCREMENTAL = "incremental"  # Incremental update
    FULL = "full"                # Full update
    SMART = "smart"              # Smart detection


@dataclass(frozen=True)
class SyncCommand:
    subscription_id: int
    url: str
    trigger: UpdateTrigger
    mode: UpdateMode
    user_id: int | None = None
    force: bool = False
    trace_id: str | None = None
    run_id: str | None = None


@dataclass(frozen=True)
class QueuedSync:
    sync_state_id: int | None
    status: str
    run_context: object | None
    queue_token: str | None
    pending_video_count: int


@dataclass
class SubscriptionUpdateRequest:
    """Subscription update request"""

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
    """Subscription update result"""

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
    """Subscription schedule result"""

    subscription_id: int
    sync_state_id: int | None
    status: str
    request_id: str | None = None
    run_id: str | None = None


@dataclass
class SubscriptionDirectRunResult:
    """Subscription direct run result"""

    subscription_id: int
    sync_state_id: int | None
    status: str
    request_id: str | None = None
    run_id: str | None = None
    result: SubscriptionUpdateResult | None = None

