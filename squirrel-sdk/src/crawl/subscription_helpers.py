"""Helpers for subscription synchronization flows."""
from __future__ import annotations

from typing import Any, Optional

from .core import SubscriptionSyncContext, SubscriptionSyncResult


def resolve_subscription_limit(
    context: SubscriptionSyncContext,
    *,
    default_incremental_limit: int = 30,
) -> Optional[int]:
    if context.mode == 'full':
        return None
    return context.limit or default_incremental_limit


def append_subscription_video_url(
    video_url: str,
    *,
    video_urls: list[str],
    context: SubscriptionSyncContext,
    latest_video_url: Optional[str],
    limit: Optional[int],
    seen_urls: Optional[set[str]] = None,
) -> tuple[Optional[str], Optional[str]]:
    updated_latest_video_url = latest_video_url or video_url

    if context.mode != 'full' and video_url == context.last_seen_video_url:
        return updated_latest_video_url, 'cursor_hit'

    if seen_urls is not None:
        if video_url in seen_urls:
            return updated_latest_video_url, None
        seen_urls.add(video_url)
    elif video_url in video_urls:
        return updated_latest_video_url, None

    video_urls.append(video_url)
    if limit is not None and len(video_urls) >= limit:
        return updated_latest_video_url, 'limit_reached'

    return updated_latest_video_url, None


def build_subscription_sync_result(
    *,
    video_urls: list[str],
    latest_video_url: Optional[str],
    context: SubscriptionSyncContext,
    stop_reason: str,
    cursor_payload: Optional[dict[str, Any]] = None,
    has_more: bool = False,
    source_video_count: Optional[int] = None,
) -> SubscriptionSyncResult:
    return SubscriptionSyncResult(
        video_urls=video_urls,
        latest_video_url=latest_video_url,
        cursor_payload=(
            cursor_payload
            if cursor_payload is not None
            else ({'latest_video_url': latest_video_url} if latest_video_url else context.cursor_payload)
        ),
        has_more=has_more,
        stop_reason=stop_reason,
        source_video_count=source_video_count,
        total_available=len(video_urls),
    )
