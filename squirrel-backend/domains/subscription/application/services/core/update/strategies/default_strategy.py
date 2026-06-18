"""Default update strategy (applicable to all sites)
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
from infrastructure.site_runtimes.gateway import SiteRuntimeGateway
from infrastructure.site_runtimes.locator import get_runtime_gateway

from ..models import SubscriptionUpdateRequest, UpdateMode
from ..video_extraction_coordinator import enqueue_discovered_videos
from .base import UpdateStrategy

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


class DefaultUpdateStrategy(UpdateStrategy):
    """Default update strategy (applicable to all sites)"""

    def __init__(self, runtime_gateway: SiteRuntimeGateway | None = None) -> None:
        self._runtime_gateway = runtime_gateway

    @property
    def site_name(self) -> str:
        return "default"

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
        runtime_gateway = self._runtime_gateway or get_runtime_gateway()
        response = runtime_gateway.invoke(
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
