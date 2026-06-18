"""Default subscription update strategy (applicable to all sites).

Historically this was one implementation of an ``UpdateStrategy`` ABC selected
through a ``StrategyRegistry``. No second strategy was ever registered, so the
ABC and registry were removed; this concrete class is the only strategy. It
keeps its public methods (``should_update``/``fetch_videos``/
``enqueue_extraction``/``execute``) because they are exercised directly by
tests and read cleanly as the update flow's phases.
"""
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import update

from domains.subscription.application.services.core.listing.service import get_subscription_detail
from domains.subscription.application.services.core.runtime_models import SubscriptionSyncResult
from domains.subscription.domain.models.subscription import Subscription as SubscriptionModel
from domains.subscription.domain.models.subscription_sync_state import SyncMode, SyncStatus
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_plugins.registry import SitePluginRegistry, get_site_plugin_registry

from ..models import SubscriptionUpdateRequest, SubscriptionUpdateResult, UpdateMode
from ..video_extraction_coordinator import enqueue_discovered_videos

logger = logging.getLogger(__name__)

FULL_BACKFILL_RETRY_COOLDOWN = timedelta(hours=6)
FULL_BACKFILL_STALE_AFTER = timedelta(days=3)


def should_schedule_total_video_backfill(
    sync_mode: str,
    local_total_videos: int | None,
    observed_total_available: int | None,
    full_sync_status: str | None,
    full_last_success_at: datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    current_time = now or datetime.now()

    if sync_mode == SyncMode.FULL.value:
        return False
    if full_sync_status in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}:
        return False

    local_total = max(int(local_total_videos or 0), 0)
    observed_total = max(int(observed_total_available), 0) if observed_total_available is not None else None

    if full_last_success_at is None:
        return True

    if local_total <= 0 and full_last_success_at <= current_time - FULL_BACKFILL_RETRY_COOLDOWN:
        return True

    if observed_total is not None and observed_total > local_total:
        return full_last_success_at <= current_time - FULL_BACKFILL_RETRY_COOLDOWN

    return full_last_success_at <= current_time - FULL_BACKFILL_STALE_AFTER


class DefaultUpdateStrategy:
    """Default update strategy (applicable to all sites)"""

    def __init__(self, plugin_registry: SitePluginRegistry | None = None) -> None:
        self._plugin_registry = plugin_registry or get_site_plugin_registry()

    @property
    def site_name(self) -> str:
        return "default"

    def execute(self, request: SubscriptionUpdateRequest) -> SubscriptionUpdateResult:
        """Run the full update flow: gate, fetch, enqueue."""
        should_update, skip_reason = self.should_update(request)
        if not should_update:
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=True,
                videos_found=0,
                videos_enqueued=0,
                skipped_reason=skip_reason,
            )

        fetch_result = self.fetch_videos(request)
        enqueued = self.enqueue_extraction(fetch_result, request)

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

    def should_update(self, request: SubscriptionUpdateRequest) -> tuple[bool, str | None]:
        """Check whether an update is needed"""
        sub = get_subscription_detail(request.subscription_id)
        if not sub or sub.is_deleted:
            return False, "subscription_not_found"
        return True, None

    def fetch_videos(self, request: SubscriptionUpdateRequest) -> SubscriptionSyncResult:
        """Fetch video list"""
        parsed_url = urlparse(request.url)
        domain = parsed_url.netloc.lower().split(":")[0]
        site_name, _ = SiteCatalog.find_site_by_domain(domain)
        if not site_name:
            raise ValueError(f"No subscription route found for domain: {domain}")

        sync_mode = UpdateMode.FULL if request.mode == UpdateMode.FULL else UpdateMode.INCREMENTAL
        response = self._plugin_registry.invoke(
            "sync_subscription",
            site_name=site_name,
            domain=domain,
            payload={
                "url": request.url,
                "mode": sync_mode.value,
                "cursor_payload": request.cursor_payload or {},
                "last_seen_video_url": request.last_seen_video_url,
                "limit": None if sync_mode == UpdateMode.FULL else settings.CHANNEL_UPDATE_DEFAULT_SIZE,
            },
        )
        if not response.ok:
            message = response.error.message if response.error else f"Subscription sync failed for domain: {domain}"
            raise ValueError(message)
        if not isinstance(response.data, dict):
            raise ValueError(f"Subscription sync payload must be an object for domain: {domain}")

        sync_result = SubscriptionSyncResult.from_dict(response.data)

        if sync_mode == UpdateMode.FULL and sync_result.total_available is not None:
            self._update_total_videos(request.subscription_id, sync_result.total_available)

        return sync_result

    def enqueue_extraction(self, fetch_result: SubscriptionSyncResult, request: SubscriptionUpdateRequest) -> int:
        """Enqueue videos for extraction"""
        return enqueue_discovered_videos(fetch_result, request)

    @staticmethod
    def _update_total_videos(subscription_id: int, total: int) -> None:
        """Update subscription total video count"""
        with get_session() as session:
            session.execute(
                update(SubscriptionModel)
                .where(SubscriptionModel.id == subscription_id)
                .values(total_videos=total),
            )
