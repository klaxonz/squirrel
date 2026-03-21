from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection


def _resolve_range(range_key: str) -> tuple[str, datetime]:
    now = datetime.now()
    normalized = str(range_key or '24h').strip().lower()
    if normalized == '30d':
        return 'day', now - timedelta(days=30)
    if normalized == '7d':
        return 'day', now - timedelta(days=7)
    return 'hour', now - timedelta(hours=24)


def _serialize_datetime(value: Optional[datetime]) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''


def _bucket_value(value: datetime, granularity: str) -> datetime:
    if granularity == 'day':
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    return value.replace(minute=0, second=0, microsecond=0)


def get_trends(
    user_id: int,
    *,
    range_key: str = '24h',
    site: Optional[str] = None,
    mode: Optional[str] = None,
    trigger: Optional[str] = None,
) -> dict:
    granularity, start_time = _resolve_range(range_key)
    filters = [
        SubscriptionSyncRunProjection.last_event_at >= start_time,
    ]
    if site:
        filters.append(SubscriptionSyncRunProjection.site == str(site).strip().lower())
    if mode:
        filters.append(SubscriptionSyncRunProjection.sync_mode == str(mode).strip().lower())
    if trigger:
        filters.append(SubscriptionSyncRunProjection.trigger == str(trigger).strip().lower())

    with get_session() as session:
        rows = session.execute(
            select(SubscriptionSyncRunProjection)
            .join(Subscription, Subscription.id == SubscriptionSyncRunProjection.subscription_id)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(and_(*filters))
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            )
            .order_by(SubscriptionSyncRunProjection.last_event_at.asc())
        ).scalars().all()

    bucket_map = {}
    site_breakdown = {}

    for row in rows:
        if not row.last_event_at:
            continue

        bucket_time = _bucket_value(row.last_event_at, granularity)
        bucket_key = (
            _serialize_datetime(bucket_time),
            row.site or '',
            row.sync_mode or '',
            row.trigger or '',
        )
        bucket = bucket_map.setdefault(bucket_key, {
            'bucket_time': _serialize_datetime(bucket_time),
            'site': row.site or '',
            'sync_mode': row.sync_mode or '',
            'trigger': row.trigger or '',
            'runs_total': 0,
            'runs_success': 0,
            'runs_failed': 0,
            'runs_deferred': 0,
            'videos_found': 0,
            'videos_enqueued': 0,
            'videos_extracted': 0,
            'videos_skipped': 0,
            'avg_duration_ms': 0,
            'p95_duration_ms': 0,
            '_durations': [],
        })

        bucket['runs_total'] += 1
        if row.status == 'success':
            bucket['runs_success'] += 1
        elif row.status in {'failed', 'timeout'}:
            bucket['runs_failed'] += 1
        elif row.status == 'deferred':
            bucket['runs_deferred'] += 1

        bucket['videos_found'] += row.videos_found
        bucket['videos_enqueued'] += row.videos_enqueued
        bucket['videos_extracted'] += row.videos_extracted
        bucket['videos_skipped'] += row.videos_skipped
        if row.duration_ms > 0:
            bucket['_durations'].append(int(row.duration_ms))

        site_key = row.site or 'unknown'
        target = site_breakdown.setdefault(site_key, {
            'site': site_key,
            'runs_total': 0,
            'runs_success': 0,
            'runs_failed': 0,
            'runs_deferred': 0,
            'videos_found': 0,
            'videos_enqueued': 0,
            'videos_extracted': 0,
        })
        target['runs_total'] += 1
        if row.status == 'success':
            target['runs_success'] += 1
        elif row.status in {'failed', 'timeout'}:
            target['runs_failed'] += 1
        elif row.status == 'deferred':
            target['runs_deferred'] += 1
        target['videos_found'] += row.videos_found
        target['videos_enqueued'] += row.videos_enqueued
        target['videos_extracted'] += row.videos_extracted

    series = []
    for bucket in bucket_map.values():
        durations = sorted(bucket.pop('_durations'))
        if durations:
            bucket['avg_duration_ms'] = int(sum(durations) / len(durations))
            index = max(0, min(len(durations) - 1, int(len(durations) * 0.95) - 1))
            bucket['p95_duration_ms'] = durations[index]
        series.append(bucket)

    series.sort(key=lambda item: item['bucket_time'])

    return {
        'range': range_key,
        'granularity': granularity,
        'series': series,
        'site_breakdown': sorted(site_breakdown.values(), key=lambda item: item['runs_total'], reverse=True),
    }
