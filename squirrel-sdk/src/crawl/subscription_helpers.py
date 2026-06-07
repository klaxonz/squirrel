"""Helpers for subscription synchronization flows."""
from __future__ import annotations

from typing import Any

from .core import SubscriptionSyncContext, SubscriptionSyncResult


def resolve_subscription_limit(
    context: SubscriptionSyncContext,
    *,
    default_incremental_limit: int = 30,
) -> int | None:
    if context.mode == 'full':
        return None
    return context.limit or default_incremental_limit


def append_subscription_video_url(
    video_url: str,
    *,
    video_urls: list[str],
    context: SubscriptionSyncContext,
    latest_video_url: str | None,
    limit: int | None,
    seen_urls: set[str] | None = None,
) -> tuple[str | None, str | None]:
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
    latest_video_url: str | None,
    context: SubscriptionSyncContext,
    stop_reason: str,
    cursor_payload: dict[str, Any] | None = None,
    has_more: bool = False,
    source_video_count: int | None = None,
    total_available: int | None = None,
    head_sample_urls: list[str] | None = None,
    anchor_found: bool | None = None,
    oldest_scanned_url: str | None = None,
    cursor_invalid: bool | None = None,
    cursor_loop_detected: bool | None = None,
    scan_depth: int | None = None,
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
        total_available=total_available,
        head_sample_urls=head_sample_urls,
        anchor_found=anchor_found,
        oldest_scanned_url=oldest_scanned_url,
        cursor_invalid=cursor_invalid,
        cursor_loop_detected=cursor_loop_detected,
        scan_depth=scan_depth,
    )
