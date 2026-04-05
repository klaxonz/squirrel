from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, or_, select

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from services.subscription_sync_progress import build_progress_snapshot
from services.subscription_sync_run_service import SyncEventType
from utils.site_catalog import SiteCatalog
from utils.site_icons import build_site_icon_url, resolve_site_icon_path

TERMINAL_RUN_STATUSES = {'success', 'failed', 'deferred', 'timeout'}
FEED_RECENT_PHASES = {'extracting', 'finalizing', 'completed'}
FEED_HANDOFF_EVENT_TYPES = {'phase_changed', 'continued'}
FEED_HANDOFF_PHASES = {'extracting', 'finalizing'}


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


def _resolve_site_icon_url(site: Optional[str]) -> Optional[str]:
    normalized_site = str(site or '').strip().lower()
    if not normalized_site:
        return None

    catalog = SiteCatalog.get_catalog() or {}

    if normalized_site in catalog:
        site_slug = normalized_site
        catalog_entry = catalog[site_slug]
    else:
        site_slug, catalog_entry = SiteCatalog.find_site_by_domain(normalized_site)
        if not site_slug:
            site_slug = None
            catalog_entry = None
            for slug, info in catalog.items():
                aliases = [str(alias or '').strip().lower() for alias in info.get('aliases', []) if alias]
                if normalized_site in aliases:
                    site_slug = slug
                    catalog_entry = info
                    break

    icon_url = str((catalog_entry or {}).get('icon_url') or '').strip() or None
    if icon_url:
        return icon_url

    fallback_slug = site_slug or normalized_site
    if resolve_site_icon_path(fallback_slug):
        return build_site_icon_url(fallback_slug)

    return None


def _payload_metric_value(session, run_id: str, key: str) -> Optional[int]:
    payloads = session.execute(
        select(SubscriptionSyncEvent.payload)
        .where(SubscriptionSyncEvent.stream_id == run_id)
        .order_by(SubscriptionSyncEvent.seq_no.desc(), SubscriptionSyncEvent.occurred_at.desc())
    ).scalars().all()

    for payload in payloads:
        payload = payload or {}
        if key not in payload:
            continue
        try:
            return int(payload.get(key))
        except (TypeError, ValueError):
            continue
    return None


def _load_feed_completed_at_map(session, run_ids: list[str]) -> dict[str, datetime]:
    if not run_ids:
        return {}

    handoff_rows = session.execute(
        select(
            SubscriptionSyncEvent.stream_id,
            func.max(SubscriptionSyncEvent.occurred_at),
        )
        .where(
            SubscriptionSyncEvent.stream_id.in_(run_ids),
            SubscriptionSyncEvent.event_type.in_(FEED_HANDOFF_EVENT_TYPES),
            SubscriptionSyncEvent.event_phase.in_(FEED_HANDOFF_PHASES),
        )
        .group_by(SubscriptionSyncEvent.stream_id)
    ).all()

    feed_completed_at_map = {
        str(stream_id): occurred_at
        for stream_id, occurred_at in handoff_rows
        if stream_id and occurred_at
    }

    unresolved_run_ids = [run_id for run_id in run_ids if run_id not in feed_completed_at_map]
    if not unresolved_run_ids:
        return feed_completed_at_map

    completed_rows = session.execute(
        select(
            SubscriptionSyncEvent.stream_id,
            func.max(SubscriptionSyncEvent.occurred_at),
        )
        .where(
            SubscriptionSyncEvent.stream_id.in_(unresolved_run_ids),
            SubscriptionSyncEvent.event_type == SyncEventType.COMPLETED,
            SubscriptionSyncEvent.event_phase == 'completed',
        )
        .group_by(SubscriptionSyncEvent.stream_id)
    ).all()

    for stream_id, occurred_at in completed_rows:
        if stream_id and occurred_at:
            feed_completed_at_map[str(stream_id)] = occurred_at

    return feed_completed_at_map


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


def _count_query_rows(session, query) -> int:
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    return int(session.execute(count_query).scalar() or 0)


def _run_exists_for_user(session, run_id: str, user_id: int) -> bool:
    row = session.execute(
        select(SubscriptionSyncRunProjection.run_id)
        .join(Subscription, Subscription.id == SubscriptionSyncRunProjection.subscription_id)
        .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
        .where(
            SubscriptionSyncRunProjection.run_id == run_id,
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            Subscription.is_deleted.is_(False),
        )
        .limit(1)
    ).first()
    return row is not None


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

    normalized_status = str(status or '').strip().lower() or None
    if normalized_status == 'recent':
        filters.append(SubscriptionSyncRunProjection.status.in_(TERMINAL_RUN_STATUSES))
    elif normalized_status == 'feed_recent':
        filters.append(
            or_(
                SubscriptionSyncRunProjection.status.in_(TERMINAL_RUN_STATUSES),
                and_(
                    SubscriptionSyncRunProjection.status == 'running',
                    SubscriptionSyncRunProjection.current_phase.in_(FEED_RECENT_PHASES),
                ),
            )
        )
    elif normalized_status:
        filters.append(SubscriptionSyncRunProjection.status == normalized_status)
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

    if normalized_status == 'feed_recent':
        base_query = base_query.join(
            SubscriptionSyncSubscriptionProjection,
            SubscriptionSyncSubscriptionProjection.subscription_id == SubscriptionSyncRunProjection.subscription_id,
        ).where(
            SubscriptionSyncSubscriptionProjection.latest_run_id == SubscriptionSyncRunProjection.run_id
        )

    with get_session() as session:
        if normalized_status == 'feed_recent':
            all_rows = session.execute(base_query).all()
            feed_completed_at_map = _load_feed_completed_at_map(
                session,
                [run.run_id for run, _ in all_rows if run and run.run_id],
            )

            def feed_recent_sort_key(row):
                run, _ = row
                feed_completed_at = feed_completed_at_map.get(run.run_id)
                return (
                    feed_completed_at or run.finished_at or run.last_event_at or run.started_at or datetime.min,
                    run.run_id,
                )

            sorted_rows = sorted(all_rows, key=feed_recent_sort_key, reverse=True)
            rows = sorted_rows[(page - 1) * page_size: page * page_size]
        else:
            rows = session.execute(
                base_query.order_by(SubscriptionSyncRunProjection.last_event_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            total = _count_query_rows(session, base_query)
            feed_completed_at_map = {}

    data = []
    for run, subscription in rows:
        progress_snapshot = build_progress_snapshot(
            status=run.status,
            current_phase=run.current_phase,
            videos_found=run.videos_found,
            videos_enqueued=run.videos_enqueued,
            videos_extracted=run.videos_extracted,
            pending_video_count=run.pending_video_count,
        )
        data.append({
            'run_id': run.run_id,
            'subscription_id': subscription.id,
            'subscription_name': subscription.name,
            'subscription_avatar': subscription.avatar,
            'site': run.site,
            'site_icon_url': _resolve_site_icon_url(run.site),
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
            'feed_completed': progress_snapshot['feed_completed'],
            'progress_percent': progress_snapshot['progress_percent'],
            'progress_label': progress_snapshot['progress_label'],
            'feed_completed_at': _serialize_datetime(feed_completed_at_map.get(run.run_id)),
            'last_event_at': _serialize_datetime(run.last_event_at),
        })

    return {
        'total': len(all_rows) if normalized_status == 'feed_recent' else total,
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
        source_video_count = _payload_metric_value(session, run.run_id, 'source_video_count')
        progress_snapshot = build_progress_snapshot(
            status=run.status,
            current_phase=run.current_phase,
            videos_found=run.videos_found,
            videos_enqueued=run.videos_enqueued,
            videos_extracted=run.videos_extracted,
            pending_video_count=run.pending_video_count,
        )
        return {
            'run_id': run.run_id,
            'subscription_id': subscription.id,
            'subscription_name': subscription.name,
            'subscription_avatar': subscription.avatar,
            'site': run.site,
            'site_icon_url': _resolve_site_icon_url(run.site),
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
            'feed_completed': progress_snapshot['feed_completed'],
            'progress_percent': progress_snapshot['progress_percent'],
            'progress_label': progress_snapshot['progress_label'],
            'last_event_at': _serialize_datetime(run.last_event_at),
            'created_at': _serialize_datetime(run.created_at),
            'updated_at': _serialize_datetime(run.updated_at),
        }


def get_run_detail_snapshot(run_id: str, user_id: int) -> dict | None:
    run = get_run_detail(run_id, user_id)
    if not run:
        return None
    return {
        'run': run,
        'events': list_run_events(run_id, user_id),
    }


def list_run_events(run_id: str, user_id: int) -> list[dict]:
    with get_session() as session:
        if not _run_exists_for_user(session, run_id, user_id):
            return []
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
