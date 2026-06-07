from __future__ import annotations

from datetime import datetime
from math import ceil

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from core.database import get_session
from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from models.subscription_sync_trend_projection import SubscriptionSyncTrendProjection
from services.subscription_sync_run_service import SyncEventType, SyncRunStatus
from services.subscription_sync_run_service import _default as _default_run_service

TREND_DURATION_BUCKETS_MS = [100, 500, 1000, 2000, 5000, 10000, 30000, 60000, 120000, 300000, 600000]


class SubscriptionSyncProjectionService:
    def __init__(self, session_factory=get_session, run_service=None):
        self.session_factory = session_factory
        self.run_service = run_service or _default_run_service

    @staticmethod
    def _payload_int(payload: dict | None, key: str, default: int = 0) -> int:
        if not payload:
            return default
        value = payload.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _payload_text(payload: dict | None, key: str, default: str | None = None) -> str | None:
        if not payload:
            return default
        value = payload.get(key)
        if value in (None, ''):
            return default
        return str(value)

    @staticmethod
    def _payload_datetime(payload: dict | None, key: str) -> datetime | None:
        if not payload or key not in payload:
            return None
        value = payload.get(key)
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            try:
                return datetime.fromisoformat(normalized)
            except ValueError:
                try:
                    return datetime.strptime(normalized, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return None
        return None

    @staticmethod
    def _normalize_dim(value: str | None) -> str:
        return str(value or '').strip()

    @staticmethod
    def _advisory_lock(session: Session, key: str) -> None:
        session.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'), {'key': key})

    @staticmethod
    def _bucket_time(value: datetime, granularity: str) -> datetime:
        if granularity == 'day':
            return value.replace(hour=0, minute=0, second=0, microsecond=0)
        return value.replace(minute=0, second=0, microsecond=0)

    @staticmethod
    def _resolve_status(event: SubscriptionSyncEvent) -> str:
        if event.event_status:
            return event.event_status
        mapping = {
            SyncEventType.RUN_CREATED: SyncRunStatus.CREATED,
            SyncEventType.QUEUED: SyncRunStatus.QUEUED,
            SyncEventType.CLAIMED: SyncRunStatus.RUNNING,
            SyncEventType.STARTED: SyncRunStatus.RUNNING,
            SyncEventType.COMPLETED: SyncRunStatus.SUCCESS,
            SyncEventType.FAILED: SyncRunStatus.FAILED,
            SyncEventType.DEFERRED: SyncRunStatus.DEFERRED,
            SyncEventType.TIMEOUT_RECOVERED: SyncRunStatus.TIMEOUT,
            SyncEventType.STALE_RUNNING_RECOVERED: SyncRunStatus.TIMEOUT,
            SyncEventType.STALE_QUEUED_RECOVERED: SyncRunStatus.FAILED,
        }
        return mapping.get(event.event_type, SyncRunStatus.RUNNING)

    @staticmethod
    def _resolve_percentile(samples: list[int], percentile: float) -> int:
        if not samples:
            return 0
        ordered = sorted(int(sample) for sample in samples)
        index = max(0, min(len(ordered) - 1, ceil(len(ordered) * percentile) - 1))
        return ordered[index]

    @staticmethod
    def _resolve_duration_bucket(duration_ms: int) -> str:
        for bucket in TREND_DURATION_BUCKETS_MS:
            if duration_ms <= bucket:
                return str(bucket)
        return 'overflow'

    @staticmethod
    def _resolve_histogram_percentile(histogram: dict | None, percentile: float) -> int:
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

    @staticmethod
    def _get_or_create_run_projection(session: Session, event: SubscriptionSyncEvent) -> SubscriptionSyncRunProjection:
        SubscriptionSyncProjectionService._advisory_lock(session, f'run-sync-projection:{event.stream_id}')
        projection = session.get(SubscriptionSyncRunProjection, event.stream_id)
        if projection:
            return projection

        projection = SubscriptionSyncRunProjection(
            run_id=event.stream_id,
            subscription_id=event.subscription_id,
            sync_state_id=event.sync_state_id,
            site=event.site,
            sync_mode=event.sync_mode,
            trigger=event.trigger,
            request_id=event.request_id,
            trace_id=event.trace_id,
            status=SyncRunStatus.CREATED,
            current_phase=None,
            last_event_seq_no=0,
            last_event_at=event.occurred_at,
            created_at=event.created_at,
            updated_at=event.created_at,
        )
        session.add(projection)
        session.flush()
        return projection

    @staticmethod
    def _get_or_create_subscription_projection(session: Session, event: SubscriptionSyncEvent) -> SubscriptionSyncSubscriptionProjection:
        SubscriptionSyncProjectionService._advisory_lock(session, f'subscription-sync-projection:{event.subscription_id}')
        projection = session.get(SubscriptionSyncSubscriptionProjection, event.subscription_id)
        if projection:
            return projection

        projection = SubscriptionSyncSubscriptionProjection(
            subscription_id=event.subscription_id,
            latest_run_id=None,
            current_status='idle',
            current_phase=None,
            last_event_seq_no=0,
            updated_at=event.occurred_at,
        )
        session.add(projection)
        session.flush()
        return projection

    @staticmethod
    def _get_or_create_trend_projection(
        session: Session,
        *,
        bucket_time: datetime,
        bucket_granularity: str,
        site: str,
        sync_mode: str,
        trigger: str,
    ) -> SubscriptionSyncTrendProjection:
        SubscriptionSyncProjectionService._advisory_lock(
            session,
            f'trend-sync-projection:{bucket_granularity}:{bucket_time.isoformat()}:{site}:{sync_mode}:{trigger}',
        )
        projection = session.execute(
            select(SubscriptionSyncTrendProjection).where(
                SubscriptionSyncTrendProjection.bucket_time == bucket_time,
                SubscriptionSyncTrendProjection.bucket_granularity == bucket_granularity,
                SubscriptionSyncTrendProjection.site == site,
                SubscriptionSyncTrendProjection.sync_mode == sync_mode,
                SubscriptionSyncTrendProjection.trigger == trigger,
            ),
        ).scalar_one_or_none()
        if projection:
            return projection

        projection = SubscriptionSyncTrendProjection(
            bucket_time=bucket_time,
            bucket_granularity=bucket_granularity,
            site=site,
            sync_mode=sync_mode,
            trigger=trigger,
            updated_at=datetime.now(),
        )
        session.add(projection)
        session.flush()
        return projection

    @staticmethod
    def _apply_counter_payload(projection: SubscriptionSyncRunProjection, event: SubscriptionSyncEvent) -> None:
        counter_by_event_type = {
            SyncEventType.VIDEO_FOUND: 'videos_found',
            SyncEventType.VIDEO_ENQUEUED: 'videos_enqueued',
            SyncEventType.VIDEO_EXTRACTED: 'videos_extracted',
            SyncEventType.VIDEO_SKIPPED: 'videos_skipped',
        }
        counter_name = counter_by_event_type.get(event.event_type)
        if not counter_name:
            return

        payload = event.payload or {}
        delta_key = f'{counter_name}_delta'
        if delta_key in payload:
            current_value = getattr(projection, counter_name)
            setattr(projection, counter_name, max(0, current_value + SubscriptionSyncProjectionService._payload_int(payload, delta_key)))
            return

        if counter_name in payload:
            current_value = getattr(projection, counter_name)
            next_value = SubscriptionSyncProjectionService._payload_int(payload, counter_name, current_value)
            setattr(projection, counter_name, max(current_value, next_value))

    @staticmethod
    def _apply_run_projection(projection: SubscriptionSyncRunProjection, event: SubscriptionSyncEvent) -> None:
        if event.seq_no <= projection.last_event_seq_no:
            return
        payload = event.payload or {}
        projection.sync_state_id = event.sync_state_id
        projection.site = event.site
        projection.sync_mode = event.sync_mode
        projection.trigger = event.trigger
        projection.request_id = event.request_id
        projection.trace_id = event.trace_id
        projection.status = SubscriptionSyncProjectionService._resolve_status(event)
        projection.current_phase = event.event_phase or projection.current_phase
        projection.last_event_seq_no = event.seq_no
        projection.last_event_at = event.occurred_at
        projection.updated_at = event.occurred_at

        if event.event_type == SyncEventType.QUEUED and not projection.queued_at:
            projection.queued_at = event.occurred_at
        if event.event_type in {SyncEventType.CLAIMED, SyncEventType.STARTED} and not projection.started_at:
            projection.started_at = event.occurred_at
        if event.event_type in {
            SyncEventType.COMPLETED,
            SyncEventType.FAILED,
            SyncEventType.DEFERRED,
            SyncEventType.TIMEOUT_RECOVERED,
            SyncEventType.STALE_RUNNING_RECOVERED,
            SyncEventType.STALE_QUEUED_RECOVERED,
        }:
            projection.finished_at = event.occurred_at

        if projection.started_at and projection.finished_at:
            projection.duration_ms = max(0, int((projection.finished_at - projection.started_at).total_seconds() * 1000))

        if 'failure_count' in payload:
            projection.failure_count = SubscriptionSyncProjectionService._payload_int(payload, 'failure_count', projection.failure_count)
        elif event.event_type in {
            SyncEventType.FAILED,
            SyncEventType.TIMEOUT_RECOVERED,
            SyncEventType.STALE_RUNNING_RECOVERED,
            SyncEventType.STALE_QUEUED_RECOVERED,
        }:
            projection.failure_count += 1

        projection.pending_video_count = SubscriptionSyncProjectionService._payload_int(payload, 'pending_video_count', projection.pending_video_count)
        projection.error_type = SubscriptionSyncProjectionService._payload_text(payload, 'error_type', projection.error_type)
        projection.error_message = SubscriptionSyncProjectionService._payload_text(payload, 'error_message', projection.error_message)
        SubscriptionSyncProjectionService._apply_counter_payload(projection, event)

    @staticmethod
    def _apply_subscription_projection(projection: SubscriptionSyncSubscriptionProjection, event: SubscriptionSyncEvent) -> None:
        incoming_status = SubscriptionSyncProjectionService._resolve_status(event)
        if projection.latest_run_id == event.stream_id:
            if event.seq_no <= projection.last_event_seq_no:
                return
        elif projection.latest_run_id:
            if event.event_type != SyncEventType.RUN_CREATED:
                return
            if projection.current_status in {SyncRunStatus.CREATED, SyncRunStatus.QUEUED, SyncRunStatus.RUNNING} and incoming_status in {
                SyncRunStatus.SUCCESS,
                SyncRunStatus.FAILED,
                SyncRunStatus.DEFERRED,
                SyncRunStatus.TIMEOUT,
            }:
                return
        payload = event.payload or {}
        projection.latest_run_id = event.stream_id
        projection.current_status = incoming_status
        projection.current_phase = event.event_phase or projection.current_phase
        projection.last_event_seq_no = event.seq_no
        projection.updated_at = event.occurred_at
        projection.pending_video_count = SubscriptionSyncProjectionService._payload_int(payload, 'pending_video_count', projection.pending_video_count)

        next_sync_at = SubscriptionSyncProjectionService._payload_datetime(payload, 'next_sync_at')
        if next_sync_at:
            projection.next_sync_at = next_sync_at

        if event.event_type in {
            SyncEventType.COMPLETED,
            SyncEventType.FAILED,
            SyncEventType.DEFERRED,
            SyncEventType.TIMEOUT_RECOVERED,
            SyncEventType.STALE_RUNNING_RECOVERED,
            SyncEventType.STALE_QUEUED_RECOVERED,
        }:
            projection.last_sync_at = event.occurred_at

        if event.event_type == SyncEventType.COMPLETED:
            projection.last_success_at = event.occurred_at
            projection.last_error_message = None
            projection.failure_streak = 0
        elif event.event_type in {
            SyncEventType.FAILED,
            SyncEventType.TIMEOUT_RECOVERED,
            SyncEventType.STALE_RUNNING_RECOVERED,
            SyncEventType.STALE_QUEUED_RECOVERED,
        }:
            projection.last_error_message = SubscriptionSyncProjectionService._payload_text(payload, 'error_message', event.message)
            projection.failure_streak += 1
        elif event.event_type == SyncEventType.DEFERRED:
            projection.last_error_message = SubscriptionSyncProjectionService._payload_text(payload, 'error_message', event.message)

    @staticmethod
    def _apply_trend_projection(session: Session, event: SubscriptionSyncEvent) -> None:
        dimensions = {
            'site': SubscriptionSyncProjectionService._normalize_dim(event.site),
            'sync_mode': SubscriptionSyncProjectionService._normalize_dim(event.sync_mode),
            'trigger': SubscriptionSyncProjectionService._normalize_dim(event.trigger),
        }
        for granularity in ('hour', 'day'):
            projection = SubscriptionSyncProjectionService._get_or_create_trend_projection(
                session,
                bucket_time=SubscriptionSyncProjectionService._bucket_time(event.occurred_at, granularity),
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
                    delta = SubscriptionSyncProjectionService._payload_int(payload, f'{field_name}_delta', 1)
                    setattr(projection, field_name, max(0, getattr(projection, field_name) + delta))

            duration_ms = SubscriptionSyncProjectionService._payload_int(payload, 'duration_ms', 0)
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
                bucket_key = SubscriptionSyncProjectionService._resolve_duration_bucket(duration_ms)
                histogram[bucket_key] = int(histogram.get(bucket_key, 0) or 0) + 1
                projection.duration_histogram = histogram
                projection.p95_duration_ms = SubscriptionSyncProjectionService._resolve_histogram_percentile(histogram, 0.95)

    def apply_event(self, event: SubscriptionSyncEvent, *, session: Session | None = None) -> SubscriptionSyncEvent:
        if session is not None:
            if event.projected_at:
                return event
            run_projection = self._get_or_create_run_projection(session, event)
            self._apply_run_projection(run_projection, event)

            subscription_projection = self._get_or_create_subscription_projection(session, event)
            self._apply_subscription_projection(subscription_projection, event)
            self._apply_trend_projection(session, event)
            event.projected_at = datetime.now()
            return event

        with self.session_factory() as managed_session:
            return self.apply_event(event, session=managed_session)

    def apply_events(self, events: list[SubscriptionSyncEvent], *, session: Session | None = None) -> list[SubscriptionSyncEvent]:
        if session is not None:
            ordered_events = sorted(events, key=lambda event: (event.occurred_at, event.stream_id, event.seq_no, event.id or 0))
            for event in ordered_events:
                self.apply_event(event, session=session)
            return events

        with self.session_factory() as managed_session:
            return self.apply_events(events, session=managed_session)


_default = SubscriptionSyncProjectionService()
apply_event = _default.apply_event
apply_events = _default.apply_events
