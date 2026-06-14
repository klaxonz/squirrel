"""Subscription update strategy base class
Each site can implement its own update strategy
"""
from abc import ABC, abstractmethod
from typing import Any

from infrastructure.observability.collector.instance import metrics

from ..models import SubscriptionUpdateRequest, SubscriptionUpdateResult


class UpdateStrategy(ABC):
    """Update strategy interface"""

    @property
    @abstractmethod
    def site_name(self) -> str:
        """Site name (e.g. 'youtube', 'bilibili')"""

    @abstractmethod
    def should_update(self, request: SubscriptionUpdateRequest) -> tuple[bool, str | None]:
        """Determine whether to update

        Returns:
            (whether to update, skip reason)

        """

    @abstractmethod
    def fetch_videos(self, request: SubscriptionUpdateRequest) -> Any:
        """Fetch video list
        """

    @abstractmethod
    def enqueue_extraction(self, fetch_result: Any, request: SubscriptionUpdateRequest) -> int:
        """Enqueue videos for extraction
        """

    def execute(self, request: SubscriptionUpdateRequest) -> SubscriptionUpdateResult:
        """Execute update flow (template method)
        """
        import infrastructure.site_catalog.url as url_helper
        try:
            domain = url_helper.extract_top_level_domain(request.url)
        except (ValueError, TypeError):
            domain = "unknown"
        tags = {"site": domain}

        should_update, skip_reason = self.should_update(request)
        if not should_update:
            metrics.counter("subscription.update.total", tags={**tags, "status": "skipped", "reason": skip_reason or "unknown"})
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=True,
                videos_found=0,
                videos_enqueued=0,
                skipped_reason=skip_reason,
            )

        try:
            fetch_result = self.fetch_videos(request)
            enqueued = self.enqueue_extraction(fetch_result, request)

            metrics.counter("subscription.update.total", tags={**tags, "status": "success"})
            metrics.counter("subscription.videos.found", value=len(fetch_result.video_urls), tags=tags)
            metrics.counter("subscription.videos.enqueued", value=enqueued, tags=tags)

            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=True,
                videos_found=len(fetch_result.video_urls),
                videos_enqueued=enqueued,
                has_more=bool(getattr(fetch_result, "has_more", False)),
                cursor_payload=fetch_result.cursor_payload,
                latest_video_url=fetch_result.latest_video_url,
                source_video_count=fetch_result.source_video_count,
                total_available=fetch_result.total_available,
                head_sample_urls=getattr(fetch_result, "head_sample_urls", None),
                anchor_found=getattr(fetch_result, "anchor_found", None),
                oldest_scanned_url=getattr(fetch_result, "oldest_scanned_url", None),
                cursor_invalid=bool(getattr(fetch_result, "cursor_invalid", False)),
                cursor_loop_detected=bool(getattr(fetch_result, "cursor_loop_detected", False)),
                scan_depth=getattr(fetch_result, "scan_depth", None),
            )
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            metrics.counter("subscription.update.total", tags={**tags, "status": "error"})
            metrics.counter("subscription.errors.total", tags={**tags, "error_type": type(exc).__name__})
            raise
