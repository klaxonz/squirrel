from __future__ import annotations

from datetime import datetime

from infrastructure.site_catalog.cache import format_datetime
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from domains.subscription.domain.models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from domains.subscription.interfaces.dto.dto.sync_dashboard_dto import SyncDashboardItemDto
from domains.subscription.application.services.core.sync.progress import SubscriptionSyncProgress
from domains.subscription.application.services.sync.presentation import resolve_display_status, summarize_error
from domains.subscription.application.services.sync.site_icons import SiteIconResolver


class SyncDashboardItemFactory:
    def __init__(self, *, progress_service: SubscriptionSyncProgress, site_icon_resolver: SiteIconResolver):
        self.progress_service = progress_service
        self.site_icon_resolver = site_icon_resolver

    def build_item(
        self,
        subscription: Subscription,
        subscription_projection: SubscriptionSyncSubscriptionProjection | None,
        run_projection: SubscriptionSyncRunProjection | None,
    ) -> SyncDashboardItemDto:
        current_status = subscription_projection.current_status if subscription_projection else None
        next_sync_at = subscription_projection.next_sync_at if subscription_projection else None
        display_status = resolve_display_status(current_status, next_sync_at)
        sync_mode = (run_projection.sync_mode if run_projection and run_projection.sync_mode else 'incremental')
        sync_status = current_status or (run_projection.status if run_projection else 'idle')
        pending_video_count = (
            subscription_projection.pending_video_count
            if subscription_projection
            else (run_projection.pending_video_count if run_projection else 0)
        )
        last_error = (
            subscription_projection.last_error_message
            if subscription_projection and subscription_projection.last_error_message
            else (run_projection.error_message if run_projection else None)
        )
        progress_snapshot = self.progress_service.build_progress_snapshot(
            status=run_projection.status if run_projection else current_status,
            current_phase=run_projection.current_phase if run_projection else (subscription_projection.current_phase if subscription_projection else None),
            videos_found=run_projection.videos_found if run_projection else 0,
            videos_enqueued=run_projection.videos_enqueued if run_projection else 0,
            videos_extracted=run_projection.videos_extracted if run_projection else 0,
            pending_video_count=pending_video_count,
        )

        return SyncDashboardItemDto(
            run_id=run_projection.run_id if run_projection else None,
            subscription_id=subscription.id,
            subscription_name=subscription.name,
            subscription_avatar=subscription.avatar,
            site=(run_projection.site if run_projection and run_projection.site else None),
            site_icon_url=self.site_icon_resolver.resolve(run_projection.site if run_projection else None),
            sync_mode=sync_mode,
            sync_status=sync_status,
            display_status=display_status,
            current_phase=run_projection.current_phase if run_projection else (subscription_projection.current_phase if subscription_projection else None),
            failure_count=(run_projection.failure_count if run_projection else 0),
            last_error=last_error,
            last_error_summary=summarize_error(last_error),
            last_sync_at=format_datetime(subscription_projection.last_sync_at if subscription_projection else None),
            last_success_at=format_datetime(subscription_projection.last_success_at if subscription_projection else None),
            next_sync_at=format_datetime(next_sync_at),
            queued_at=format_datetime(run_projection.queued_at if run_projection else None),
            locked_at=format_datetime(run_projection.started_at if run_projection else None),
            updated_at=format_datetime(subscription_projection.updated_at if subscription_projection else (run_projection.updated_at if run_projection else None)),
            pending_video_count=pending_video_count,
            feed_completed=bool(progress_snapshot['feed_completed']),
            has_more_pages=False,
            videos_found=run_projection.videos_found if run_projection else 0,
            videos_enqueued=run_projection.videos_enqueued if run_projection else 0,
            videos_extracted=run_projection.videos_extracted if run_projection else 0,
            videos_skipped=run_projection.videos_skipped if run_projection else 0,
            progress_percent=int(progress_snapshot['progress_percent']),
            progress_label=str(progress_snapshot['progress_label']),
            is_deferred=display_status == 'deferred',
            defer_reason='queue_backpressure' if display_status == 'deferred' else None,
        )

    def serialize_recent_run(
        self,
        run_projection: SubscriptionSyncRunProjection,
        subscription: Subscription,
        feed_completed_at: datetime | None,
    ) -> dict:
        progress_snapshot = self.progress_service.build_progress_snapshot(
            status=run_projection.status,
            current_phase=run_projection.current_phase,
            videos_found=run_projection.videos_found,
            videos_enqueued=run_projection.videos_enqueued,
            videos_extracted=run_projection.videos_extracted,
            pending_video_count=run_projection.pending_video_count,
        )
        return {
            'run_id': run_projection.run_id,
            'subscription_id': subscription.id,
            'subscription_name': subscription.name,
            'subscription_avatar': subscription.avatar,
            'site': run_projection.site,
            'site_icon_url': self.site_icon_resolver.resolve(run_projection.site),
            'sync_mode': run_projection.sync_mode,
            'trigger': run_projection.trigger,
            'status': run_projection.status,
            'current_phase': run_projection.current_phase,
            'request_id': run_projection.request_id,
            'trace_id': run_projection.trace_id,
            'queued_at': format_datetime(run_projection.queued_at),
            'started_at': format_datetime(run_projection.started_at),
            'finished_at': format_datetime(run_projection.finished_at),
            'duration_ms': run_projection.duration_ms,
            'failure_count': run_projection.failure_count,
            'error_type': run_projection.error_type,
            'error_message': run_projection.error_message,
            'videos_found': run_projection.videos_found,
            'videos_enqueued': run_projection.videos_enqueued,
            'videos_extracted': run_projection.videos_extracted,
            'videos_skipped': run_projection.videos_skipped,
            'pending_video_count': run_projection.pending_video_count,
            'feed_completed': progress_snapshot['feed_completed'],
            'progress_percent': progress_snapshot['progress_percent'],
            'progress_label': progress_snapshot['progress_label'],
            'feed_completed_at': format_datetime(feed_completed_at),
            'last_event_at': format_datetime(run_projection.last_event_at),
        }
