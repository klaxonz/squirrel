from __future__ import annotations

from typing import Any

from sites.crawl import (
    ExtractionResult,
    LoginStatusResult,
    SubscriptionImportBatchResult,
    SubscriptionImportItem,
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    VideoMeta,
)

from .auth import check_bilibili_login_status
from .importer import BilibiliUserSubscriptionImporter
from .subscription import BilibiliSubscription

DEFAULT_SITE_METADATA = {
    "label": "Bilibili",
    "aliases": ["bili"],
    "http": {
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Referer": "https://www.bilibili.com",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        }
    },
    "rate_limit": {
        "enabled": True,
        "min_interval": 3.0,
        "max_interval": 5.0,
    },
    "proxy": {
        "connect_timeout": 30.0,
        "read_timeout": 120.0,
        "write_timeout": 30.0,
        "pool_timeout": 30.0,
        "keepalive_expiry": 30.0,
        "max_connections": 50,
        "max_keepalive_connections": 50,
        "chunk_size": 2 * 1024 * 1024,
        "max_retries": 5,
        "enable_http2": True,
        "follow_redirects": True,
    },
    "login": {
        "check_url": "https://api.bilibili.com/x/web-interface/nav",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
        },
        "timeout": 15.0,
    },
    "metadata": {
        "requires_cookies": True,
        "requires_login": True,
        "offline_thumbnails_download": True,
        "offline_thumbnails_display": False,
        "nsfw": False,
    },
}

_SITE_DESCRIPTOR = {
    "site_name": "bilibili",
    "domains": ["bilibili.com", "b23.tv"],
    "test_url": "https://www.bilibili.com",
    "metadata": DEFAULT_SITE_METADATA,
}


def _build_import_batch(
    items: list[SubscriptionImportItem],
    *,
    cursor_payload: dict[str, Any] | None,
    limit: int | None,
) -> SubscriptionImportBatchResult:
    """Paginate the full subscription list using an offset cursor."""
    offset = 0
    if cursor_payload:
        try:
            offset = max(int(cursor_payload.get("offset", 0) or 0), 0)
        except (TypeError, ValueError):
            offset = 0

    normalized_limit: int | None
    try:
        normalized_limit = int(limit) if limit is not None else None
    except (TypeError, ValueError):
        normalized_limit = None
    if normalized_limit is not None and normalized_limit <= 0:
        normalized_limit = None

    if normalized_limit is None:
        batch_items = list(items[offset:])
    else:
        batch_items = list(items[offset:offset + normalized_limit])

    next_offset = offset + len(batch_items)
    has_more = next_offset < len(items)
    return SubscriptionImportBatchResult(
        items=batch_items,
        cursor_payload={"offset": next_offset} if has_more else None,
        has_more=has_more,
        stop_reason="batch_exhausted" if has_more else "source_exhausted",
        total_available=len(items),
    )


class BilibiliSiteRuntime:
    """Typed Bilibili integration surface.

    No manifest, no capability RPC: consumers call these methods directly and
    handle the crawl exceptions (AuthError/NetworkError/ParseError/
    RateLimitError) themselves.
    """

    def start(self, context: dict[str, Any] | None = None) -> None:
        return None

    def stop(self) -> None:
        return None

    def check_login_status(self) -> LoginStatusResult:
        return check_bilibili_login_status()

    def import_subscriptions(
        self,
        *,
        cursor_payload: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> SubscriptionImportBatchResult:
        items = BilibiliUserSubscriptionImporter().get_user_subscriptions()
        return _build_import_batch(items, cursor_payload=cursor_payload, limit=limit)

    def resolve_subscription(self, url: str, *, domain: str | None = None) -> SubscriptionMeta:
        return BilibiliSubscription(url=url).get_subscribe_info()

    def sync_subscription(
        self,
        url: str,
        *,
        mode: str = "incremental",
        cursor_payload: dict[str, Any] | None = None,
        last_seen_video_url: str | None = None,
        limit: int | None = None,
    ) -> SubscriptionSyncResult:
        context = SubscriptionSyncContext(
            mode=mode,
            cursor_payload=cursor_payload,
            last_seen_video_url=last_seen_video_url,
            limit=limit,
        )
        return BilibiliSubscription(url=url).sync_videos(context)

    def extract_video(self, url: str) -> ExtractionResult:
        from .video_api import build_base_info, fetch_video_info

        info, context, page_info = fetch_video_info(url)
        base_info = build_base_info(info, context, page_info)
        video_meta = VideoMeta(
            title=base_info.get("title") or "",
            url=url,
            thumbnail=base_info.get("thumbnail"),
            duration=base_info.get("duration"),
            publish_date=base_info.get("publish_date"),
            extra_data={
                "id": base_info.get("id"),
                "bvid": base_info.get("bvid"),
                "aid": base_info.get("aid"),
                "cid": base_info.get("cid"),
                "description": base_info.get("description"),
                "owner": base_info.get("owner"),
                "pages": base_info.get("pages"),
                "dynamic": base_info.get("dynamic"),
                "upload_date": base_info.get("upload_date"),
            },
        )
        return ExtractionResult.success_result(video_meta)

    def site_descriptor(self) -> dict[str, Any]:
        return dict(_SITE_DESCRIPTOR)


def get_site_runtime() -> BilibiliSiteRuntime:
    return BilibiliSiteRuntime()
