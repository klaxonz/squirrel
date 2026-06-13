from __future__ import annotations

from datetime import datetime

from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_event import SubscriptionSyncEvent
from domains.subscription.domain.models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from domains.subscription.application.services.core.sync.progress import SubscriptionSyncProgress
from domains.subscription.application.services.sync.site_icons import SiteIconResolver


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        try:
            return datetime.strptime(normalized, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None


def serialize_datetime(value: datetime | None) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''


def serialize_run(
    run: SubscriptionSyncRunProjection,
    subscription: Subscription,
    *,
    progress_service: SubscriptionSyncProgress,
    site_icon_resolver: SiteIconResolver,
    feed_completed_at: datetime | None = None,
    include_feed_completed_at: bool = False,
    source_video_count: int | None = None,
    include_detail_fields: bool = False,
) -> dict:
    progress_snapshot = progress_service.build_progress_snapshot(
        status=run.status,
        current_phase=run.current_phase,
        videos_found=run.videos_found,
        videos_enqueued=run.videos_enqueued,
        videos_extracted=run.videos_extracted,
        pending_video_count=run.pending_video_count,
    )
    data = {
        'run_id': run.run_id,
        'subscription_id': subscription.id,
        'subscription_name': subscription.name,
        'subscription_avatar': subscription.avatar,
        'site': run.site,
        'site_icon_url': site_icon_resolver.resolve(run.site),
        'sync_mode': run.sync_mode,
        'trigger': run.trigger,
        'status': run.status,
        'current_phase': run.current_phase,
        'request_id': run.request_id,
        'trace_id': run.trace_id,
        'queued_at': serialize_datetime(run.queued_at),
        'started_at': serialize_datetime(run.started_at),
        'finished_at': serialize_datetime(run.finished_at),
        'duration_ms': run.duration_ms,
        'failure_count': run.failure_count,
        'error_type': run.error_type,
        'error_message': run.error_message,
        'videos_found': run.videos_found,
        'videos_enqueued': run.videos_enqueued,
        'videos_extracted': run.videos_extracted,
        'videos_skipped': run.videos_skipped,
        'pending_video_count': run.pending_video_count,
        'feed_completed': progress_snapshot['feed_completed'],
        'progress_percent': progress_snapshot['progress_percent'],
        'progress_label': progress_snapshot['progress_label'],
        'last_event_at': serialize_datetime(run.last_event_at),
    }
    if include_feed_completed_at:
        data['feed_completed_at'] = serialize_datetime(feed_completed_at)
    if include_detail_fields:
        data.update({
            'source_video_count': source_video_count,
            'created_at': serialize_datetime(run.created_at),
            'updated_at': serialize_datetime(run.updated_at),
        })
    return data


def serialize_event(event: SubscriptionSyncEvent) -> dict:
    return {
        'id': event.id,
        'stream_id': event.stream_id,
        'subscription_id': event.subscription_id,
        'sync_state_id': event.sync_state_id,
        'site': event.site,
        'sync_mode': event.sync_mode,
        'trigger': event.trigger,
        'request_id': event.request_id,
        'trace_id': event.trace_id,
        'event_type': event.event_type,
        'event_phase': event.event_phase,
        'event_status': event.event_status,
        'seq_no': event.seq_no,
        'message': event.message,
        'payload': event.payload or {},
        'occurred_at': serialize_datetime(event.occurred_at),
        'projected_at': serialize_datetime(event.projected_at),
    }
