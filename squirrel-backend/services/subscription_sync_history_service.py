from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from services.subscription_sync_run_service import SyncEventType
from utils.site_catalog import SiteCatalog


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
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


def _serialize_datetime(value: Optional[datetime]) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''


def _payload_metric_value(run_id: str, key: str) -> Optional[int]:
    with get_session() as session:
        events = session.execute(
            select(SubscriptionSyncEvent)
            .where(SubscriptionSyncEvent.stream_id == run_id)
            .order_by(SubscriptionSyncEvent.seq_no.desc(), SubscriptionSyncEvent.occurred_at.desc())
        ).scalars().all()

    for event in events:
        payload = event.payload or {}
        if key not in payload:
            continue
        try:
            return int(payload.get(key))
        except (TypeError, ValueError):
            continue
    return None


def _base_run_query(user_id: int):
    return (
        select(SubscriptionSyncRunProjection, Subscription)
        .join(Subscription, Subscription.id == SubscriptionSyncRunProjection.subscription_id)
        .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            Subscription.is_deleted.is_(False),
        )
    )


def list_runs(
    user_id: int,
    *,
    status: Optional[str] = None,
    site: Optional[str] = None,
    subscription_id: Optional[int] = None,
    mode: Optional[str] = None,
    trigger: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    base_query = _base_run_query(user_id)
    filters = []

    if status:
        filters.append(SubscriptionSyncRunProjection.status == str(status).strip().lower())
    if site:
        site_candidates = SiteCatalog.expand_site_filter_values(site)
        filters.append(SubscriptionSyncRunProjection.site.in_(site_candidates))
    if subscription_id:
        filters.append(Subscription.id == subscription_id)
    if mode:
        filters.append(SubscriptionSyncRunProjection.sync_mode == str(mode).strip().lower())
    if trigger:
        filters.append(SubscriptionSyncRunProjection.trigger == str(trigger).strip().lower())

    parsed_from = _parse_datetime(date_from)
    parsed_to = _parse_datetime(date_to)
    if parsed_from:
        filters.append(SubscriptionSyncRunProjection.last_event_at >= parsed_from)
    if parsed_to:
        filters.append(SubscriptionSyncRunProjection.last_event_at <= parsed_to)

    if filters:
        base_query = base_query.where(and_(*filters))

    with get_session() as session:
        rows = session.execute(
            base_query.order_by(SubscriptionSyncRunProjection.last_event_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        all_rows = session.execute(base_query).all()

    data = []
    for run, subscription in rows:
        data.append({
            'run_id': run.run_id,
            'subscription_id': subscription.id,
            'subscription_name': subscription.name,
            'subscription_avatar': subscription.avatar,
            'site': run.site,
            'sync_mode': run.sync_mode,
            'trigger': run.trigger,
            'status': run.status,
            'current_phase': run.current_phase,
            'request_id': run.request_id,
            'trace_id': run.trace_id,
            'queued_at': _serialize_datetime(run.queued_at),
            'started_at': _serialize_datetime(run.started_at),
            'finished_at': _serialize_datetime(run.finished_at),
            'duration_ms': run.duration_ms,
            'failure_count': run.failure_count,
            'error_type': run.error_type,
            'error_message': run.error_message,
            'videos_found': run.videos_found,
            'videos_enqueued': run.videos_enqueued,
            'videos_extracted': run.videos_extracted,
            'videos_skipped': run.videos_skipped,
            'pending_video_count': run.pending_video_count,
            'last_event_at': _serialize_datetime(run.last_event_at),
        })

    return {
        'total': len(all_rows),
        'page': page,
        'pageSize': page_size,
        'data': data,
    }
def get_run_detail(run_id: str, user_id: int) -> Optional[dict]:
    with get_session() as session:
        row = session.execute(
            _base_run_query(user_id).where(SubscriptionSyncRunProjection.run_id == run_id)
        ).first()
        if not row:
            return None
        run, subscription = row
        source_video_count = _payload_metric_value(run.run_id, 'source_video_count')
        return {
            'run_id': run.run_id,
            'subscription_id': subscription.id,
            'subscription_name': subscription.name,
            'subscription_avatar': subscription.avatar,
            'site': run.site,
            'sync_mode': run.sync_mode,
            'trigger': run.trigger,
            'status': run.status,
            'current_phase': run.current_phase,
            'request_id': run.request_id,
            'trace_id': run.trace_id,
            'queued_at': _serialize_datetime(run.queued_at),
            'started_at': _serialize_datetime(run.started_at),
            'finished_at': _serialize_datetime(run.finished_at),
            'duration_ms': run.duration_ms,
            'failure_count': run.failure_count,
            'error_type': run.error_type,
            'error_message': run.error_message,
            'videos_found': run.videos_found,
            'videos_enqueued': run.videos_enqueued,
            'videos_extracted': run.videos_extracted,
            'videos_skipped': run.videos_skipped,
            'source_video_count': source_video_count,
            'pending_video_count': run.pending_video_count,
            'last_event_at': _serialize_datetime(run.last_event_at),
            'created_at': _serialize_datetime(run.created_at),
            'updated_at': _serialize_datetime(run.updated_at),
        }


def list_run_events(run_id: str, user_id: int) -> list[dict]:
    detail = get_run_detail(run_id, user_id)
    if not detail:
        return []

    with get_session() as session:
        events = session.execute(
            select(SubscriptionSyncEvent)
            .where(SubscriptionSyncEvent.stream_id == run_id)
            .order_by(SubscriptionSyncEvent.seq_no.asc(), SubscriptionSyncEvent.occurred_at.asc())
        ).scalars().all()

    data = []
    for event in events:
        data.append({
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
            'occurred_at': _serialize_datetime(event.occurred_at),
            'projected_at': _serialize_datetime(event.projected_at),
        })
    return data


def get_recovery_summary(user_id: int, hours: int = 24) -> dict:
    since = datetime.now() - timedelta(hours=hours)
    recovery_types = [
        SyncEventType.STALE_QUEUED_RECOVERED,
        SyncEventType.STALE_RUNNING_RECOVERED,
    ]

    with get_session() as session:
        rows = session.execute(
            select(SubscriptionSyncEvent)
            .join(Subscription, Subscription.id == SubscriptionSyncEvent.subscription_id)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
                SubscriptionSyncEvent.event_type.in_(recovery_types),
                SubscriptionSyncEvent.occurred_at >= since,
            )
            .order_by(SubscriptionSyncEvent.occurred_at.desc())
        ).scalars().all()

    by_type = {}
    for row in rows:
        by_type[row.event_type] = by_type.get(row.event_type, 0) + 1

    return {
        'last_reconcile_at': _serialize_datetime(rows[0].occurred_at if rows else None),
        'total_recovered': len(rows),
        'by_type': by_type,
        'window_hours': hours,
    }
