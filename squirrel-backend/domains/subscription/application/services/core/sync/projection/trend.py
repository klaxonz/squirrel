from __future__ import annotations

from datetime import datetime
from math import ceil

from sqlalchemy.orm import Session

from domains.subscription.domain.models.subscription_sync_event import SubscriptionSyncEvent
from domains.subscription.application.services.core.sync.projection.payload import payload_int
from domains.subscription.application.services.core.sync.projection.store import get_or_create_trend_projection
from domains.subscription.application.services.core.sync.run_service import SyncEventType

TREND_DURATION_BUCKETS_MS = [100, 500, 1000, 2000, 5000, 10000, 30000, 60000, 120000, 300000, 600000]


def apply_trend_projection(session: Session, event: SubscriptionSyncEvent) -> None:
    dimensions = {
        'site': normalize_dim(event.site),
        'sync_mode': normalize_dim(event.sync_mode),
        'trigger': normalize_dim(event.trigger),
    }
    for granularity in ('hour', 'day'):
        projection = get_or_create_trend_projection(
            session,
            bucket_time=bucket_time(event.occurred_at, granularity),
            bucket_granularity=granularity,
            **dimensions,
        )
        projection.updated_at = event.occurred_at

        payload = event.payload or {}
        if event.event_type in {
            SyncEventType.COMPLETED,
            SyncEventType.FAILED,
            SyncEventType.DEFERRED,
            SyncEventType.TIMEOUT_RECOVERED,
            SyncEventType.STALE_RUNNING_RECOVERED,
            SyncEventType.STALE_QUEUED_RECOVERED,
        }:
            projection.runs_total += 1
        if event.event_type == SyncEventType.COMPLETED:
            projection.runs_success += 1
        elif event.event_type in {
            SyncEventType.FAILED,
            SyncEventType.TIMEOUT_RECOVERED,
            SyncEventType.STALE_RUNNING_RECOVERED,
            SyncEventType.STALE_QUEUED_RECOVERED,
        }:
            projection.runs_failed += 1
        elif event.event_type == SyncEventType.DEFERRED:
            projection.runs_deferred += 1

        for event_type, field_name in (
            (SyncEventType.VIDEO_FOUND, 'videos_found'),
            (SyncEventType.VIDEO_ENQUEUED, 'videos_enqueued'),
            (SyncEventType.VIDEO_EXTRACTED, 'videos_extracted'),
            (SyncEventType.VIDEO_SKIPPED, 'videos_skipped'),
        ):
            if event.event_type == event_type:
                delta = payload_int(payload, f'{field_name}_delta', 1)
                setattr(projection, field_name, max(0, getattr(projection, field_name) + delta))

        duration_ms = payload_int(payload, 'duration_ms', 0)
        if duration_ms > 0 and event.event_type in {
            SyncEventType.COMPLETED,
            SyncEventType.FAILED,
            SyncEventType.TIMEOUT_RECOVERED,
            SyncEventType.STALE_RUNNING_RECOVERED,
            SyncEventType.STALE_QUEUED_RECOVERED,
        }:
            projection.duration_count += 1
            projection.duration_total_ms += duration_ms
            projection.avg_duration_ms = int(projection.duration_total_ms / projection.duration_count)
            histogram = dict(projection.duration_histogram or {})
            bucket_key = resolve_duration_bucket(duration_ms)
            histogram[bucket_key] = int(histogram.get(bucket_key, 0) or 0) + 1
            projection.duration_histogram = histogram
            projection.p95_duration_ms = resolve_histogram_percentile(histogram, 0.95)


def normalize_dim(value: str | None) -> str:
    return str(value or '').strip()


def bucket_time(value: datetime, granularity: str) -> datetime:
    if granularity == 'day':
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    return value.replace(minute=0, second=0, microsecond=0)


def resolve_duration_bucket(duration_ms: int) -> str:
    for bucket in TREND_DURATION_BUCKETS_MS:
        if duration_ms <= bucket:
            return str(bucket)
    return 'overflow'


def resolve_histogram_percentile(histogram: dict | None, percentile: float) -> int:
    if not histogram:
        return 0
    total = sum(int(value or 0) for value in histogram.values())
    if total <= 0:
        return 0

    threshold = max(1, ceil(total * percentile))
    cumulative = 0
    ordered_keys = [str(bucket) for bucket in TREND_DURATION_BUCKETS_MS] + ['overflow']
    for key in ordered_keys:
        cumulative += int(histogram.get(key, 0) or 0)
        if cumulative >= threshold:
            return TREND_DURATION_BUCKETS_MS[-1] if key == 'overflow' else int(key)
    return TREND_DURATION_BUCKETS_MS[-1]
