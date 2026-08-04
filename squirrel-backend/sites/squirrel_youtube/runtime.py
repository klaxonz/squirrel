from __future__ import annotations

from typing import Any

from sites.crawl import (
    ExtractionResult,
    ExtractionTask,
    LoginStatusResult,
    SubscriptionImportBatchResult,
    SubscriptionImportItem,
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
)

from .auth import check_youtube_login_status
from .extractor import YoutubeExtractor
from .importer import YoutubeUserSubscriptionImporter
from .subscription import YoutubeSubscription
from .youtubei_resolver import prewarm_youtubei_worker, shutdown_youtubei_worker

DEFAULT_SITE_METADATA = {
    "label": "YouTube",
    "aliases": ["yt"],
    "http": {
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
    },
    "rate_limit": {
        "enabled": True,
        "min_interval": 2.0,
        "max_interval": 5.0,
    },
    "proxy": {
        "connect_timeout": 30.0,
        "read_timeout": 180.0,
        "write_timeout": 30.0,
        "pool_timeout": 30.0,
        "keepalive_expiry": 60.0,
        "max_connections": 100,
        "max_keepalive_connections": 50,
        "chunk_size": 2 * 1024 * 1024,
        "max_retries": 5,
        "enable_http2": True,
        "follow_redirects": True,
    },
    "login": {
        "check_url": "https://www.youtube.com/feed/channels",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
        "timeout": 20.0,
    },
    "cookie": {
        "alias_domains": ["googlevideo.com", "gvt1.com", "ytimg.com"],
        "match_domain": "youtube.com",
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
    "site_name": "youtube",
    "domains": ["youtube.com", "youtu.be"],
    "test_url": "https://www.youtube.com",
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


class YoutubeSiteRuntime:
    """Typed YouTube integration surface.

    No manifest, no capability RPC: consumers call these methods directly and
    handle the crawl exceptions (AuthError/NetworkError/ParseError/
    RateLimitError) themselves.
    """

    def start(self, context: dict[str, Any] | None = None) -> None:
        prewarm_youtubei_worker()

    def stop(self) -> None:
        shutdown_youtubei_worker()

    def check_login_status(self) -> LoginStatusResult:
        return check_youtube_login_status()

    def import_subscriptions(
        self,
        *,
        cursor_payload: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> SubscriptionImportBatchResult:
        items = YoutubeUserSubscriptionImporter().get_user_subscriptions()
        return _build_import_batch(items, cursor_payload=cursor_payload, limit=limit)

    def resolve_subscription(self, url: str, *, domain: str | None = None) -> SubscriptionMeta:
        return YoutubeSubscription(url=url).get_subscribe_info()

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
        return YoutubeSubscription(url=url).sync_videos(context)

    def extract_video(self, url: str) -> ExtractionResult:
        return YoutubeExtractor().extract(ExtractionTask(url=url, site_name="youtube"))

    def site_descriptor(self) -> dict[str, Any]:
        return dict(_SITE_DESCRIPTOR)


def get_site_runtime() -> YoutubeSiteRuntime:
    return YoutubeSiteRuntime()
