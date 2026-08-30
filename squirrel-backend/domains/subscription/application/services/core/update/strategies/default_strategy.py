"""Default subscription update strategy (applicable to all sites).

Historically this was one implementation of an ``UpdateStrategy`` ABC selected
through a ``StrategyRegistry``. No second strategy was ever registered, so the
ABC and registry were removed; this concrete class is the only strategy. It
keeps its public methods (``should_update``/``fetch_videos``/
``enqueue_extraction``/``execute``) because they are exercised directly by
tests and read cleanly as the update flow's phases.
"""

import logging
from urllib.parse import urlparse

from domains.subscription.application.services.core.listing.service import SubscriptionListService
from domains.subscription.application.services.core.runtime_models import SubscriptionSyncResult
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_registry.registry import SiteRegistry, get_site_registry
from shared_kernel.infrastructure.deadline import DeadlineExceeded, run_with_deadline

from ..errors import SubscriptionUpdateError
from ..models import SubscriptionUpdateRequest, SubscriptionUpdateResult, UpdateMode
from ..video_extraction_coordinator import VideoExtractionCoordinator

logger = logging.getLogger(__name__)

# sync_subscription is the one crawl call that can genuinely wedge for the
# full crawl window; run it behind a subprocess deadline (terminate -> kill).
SYNC_DEADLINE_SECONDS = 120.0


class _SiteSyncErrorPayload(Exception):
    """Picklable carrier for a crawl SiteError raised inside the deadline child."""

    def __init__(self, payload: dict):
        super().__init__(str(payload.get('message')))
        self.payload = payload
        # Exception pickling reconstructs via cls(*args); keep the payload as
        # the single arg so category/retryable survive the process boundary.
        self.args = (payload,)


def _invoke_site_sync(
    site_name: str,
    url: str,
    mode: str,
    cursor_payload: dict,
    last_seen_video_url: str | None,
    limit: int | None,
) -> dict:
    """Run one sync_subscription in the deadline-managed child process.

    Runs in the child: loads the site runtime fresh and returns the sync
    result dict. Crawl errors are carried back as a picklable payload so the
    parent can map them to SubscriptionUpdateError with the real category.
    """
    from sites.crawl import SiteError as _SiteError

    site = get_site_registry().get_site_runtime(site_name)
    try:
        result = site.sync_subscription(
            url,
            mode=mode,
            cursor_payload=cursor_payload,
            last_seen_video_url=last_seen_video_url,
            limit=limit,
        )
    except _SiteError as exc:
        raise _SiteSyncErrorPayload(
            {
                'message': str(exc),
                'category': str(exc.category.value),
                'retryable': bool(exc.retryable),
                'retry_after': getattr(exc, 'retry_after', None),
            }
        ) from None
    return result.to_dict()


class DefaultUpdateStrategy:
    """Default update strategy (applicable to all sites)"""

    def __init__(
        self,
        registry: SiteRegistry | None = None,
        video_coordinator: VideoExtractionCoordinator | None = None,
        session_factory=None,
        listing_service: SubscriptionListService | None = None,
    ) -> None:
        self._registry = registry or get_site_registry()
        self._video_coordinator = video_coordinator or VideoExtractionCoordinator()
        self._listing_service = listing_service or SubscriptionListService(
            session_factory=session_factory or get_session,
        )
    @property
    def site_name(self) -> str:
        return 'default'

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
            has_more=bool(getattr(fetch_result, 'has_more', False)),
            cursor_payload=fetch_result.cursor_payload,
            latest_video_url=fetch_result.latest_video_url,
            source_video_count=fetch_result.source_video_count,
            total_available=fetch_result.total_available,
            head_sample_urls=getattr(fetch_result, 'head_sample_urls', None),
            anchor_found=getattr(fetch_result, 'anchor_found', None),
            oldest_scanned_url=getattr(fetch_result, 'oldest_scanned_url', None),
            cursor_invalid=bool(getattr(fetch_result, 'cursor_invalid', False)),
            cursor_loop_detected=bool(getattr(fetch_result, 'cursor_loop_detected', False)),
            scan_depth=getattr(fetch_result, 'scan_depth', None),
        )

    def should_update(self, request: SubscriptionUpdateRequest) -> tuple[bool, str | None]:
        """Check whether an update is needed."""
        sub = self._listing_service.get_subscription_detail(request.subscription_id)
        if not sub or sub.is_deleted:
            return False, 'subscription_not_found'
        return True, None

    def fetch_videos(self, request: SubscriptionUpdateRequest) -> SubscriptionSyncResult:
        """Fetch video list"""
        parsed_url = urlparse(request.url)
        domain = parsed_url.netloc.lower().split(':')[0]
        site_name, _ = SiteCatalog.find_site_by_domain(domain)
        if not site_name:
            raise ValueError(f'No subscription route found for domain: {domain}')

        sync_mode = UpdateMode.FULL if request.mode == UpdateMode.FULL else UpdateMode.INCREMENTAL
        try:
            data = run_with_deadline(
                _invoke_site_sync,
                (
                    site_name,
                    request.url,
                    sync_mode.value,
                    request.cursor_payload or {},
                    request.last_seen_video_url,
                    None if sync_mode == UpdateMode.FULL else settings.CHANNEL_UPDATE_DEFAULT_SIZE,
                ),
                timeout_seconds=SYNC_DEADLINE_SECONDS,
            )
        except _SiteSyncErrorPayload as exc:
            payload = exc.payload
            raise SubscriptionUpdateError(
                payload['message'],
                retryable=bool(payload['retryable']),
                error_type=str(payload['category']),
                retry_after_seconds=payload.get('retry_after'),
            ) from None
        except DeadlineExceeded as exc:
            raise SubscriptionUpdateError(
                str(exc),
                retryable=True,
                error_type='deadline_exceeded',
            ) from None
        if not isinstance(data, dict):
            raise ValueError(f'Subscription sync payload must be an object for domain: {domain}')

        sync_result = SubscriptionSyncResult.from_dict(data)

        return sync_result

    def enqueue_extraction(self, fetch_result: SubscriptionSyncResult, request: SubscriptionUpdateRequest) -> int:
        """Enqueue videos for extraction"""
        return self._video_coordinator.enqueue_discovered_videos(fetch_result, request)
