from __future__ import annotations

import logging
import select as io_select
from datetime import datetime, timedelta
from threading import Event
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from core.config import settings
from core.database import engine, get_session
from models.outbox_event import OutboxEvent
from models.subscription_sync_state import SubscriptionSyncState, SyncMode

logger = logging.getLogger(__name__)


class RetryLaterError(Exception):
    def __init__(self, delay_seconds: int):
        super().__init__(f'retry later in {delay_seconds} seconds')
        self.delay_seconds = delay_seconds


def publish_event(
    *,
    event_type: str,
    event_key: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: Optional[dict] = None,
    priority: str = 'normal',
    available_at: Optional[datetime] = None,
    max_attempts: int = 3,
) -> OutboxEvent:
    with get_session() as session:
        event = OutboxEvent(
            event_type=event_type,
            event_key=event_key,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload=payload or {},
            priority=priority,
            available_at=available_at or datetime.now(),
            max_attempts=max_attempts,
        )
        session.add(event)
        try:
            session.flush()
            _notify_new_event(session, event_type=event_type)
            return event
        except IntegrityError:
            session.rollback()
            existing = session.execute(
                select(OutboxEvent).where(OutboxEvent.event_key == event_key)
            ).scalar_one()
            return existing


def consume_available_events(*, limit: int = 50, now: Optional[datetime] = None, worker_id: str = 'scheduler') -> dict[str, int]:
    now = now or datetime.now()
    processed = 0
    failed = 0

    with get_session() as session:
        events = session.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.status == 'pending',
                OutboxEvent.available_at <= now,
            )
            .order_by(OutboxEvent.available_at.asc(), OutboxEvent.id.asc())
            .limit(limit)
        ).scalars().all()

        event_ids = [event.id for event in events]
        for event in events:
            event.status = 'processing'
            event.locked_by = worker_id
            event.locked_at = now
        session.flush()

    for event_id in event_ids:
        try:
            _handle_claimed_event(event_id=event_id, worker_id=worker_id, now=now)
            processed += 1
        except RetryLaterError as exc:
            _reschedule_event(event_id=event_id, delay_seconds=exc.delay_seconds, now=now)
        except Exception as exc:
            failed += 1
            logger.exception('Failed to consume outbox event id=%s', event_id)
            _mark_event_failed(event_id=event_id, error_message=str(exc), now=now)

    return {'processed': processed, 'failed': failed}


def _handle_claimed_event(*, event_id: int, worker_id: str, now: datetime) -> None:
    with get_session() as session:
        event = session.get(OutboxEvent, event_id)
        if not event or event.status != 'processing' or event.locked_by != worker_id:
            return

        _handle_event(event)
        event.status = 'done'
        event.processed_at = now
        event.last_error = None
        event.locked_by = None
        event.locked_at = None
        session.flush()


def _handle_event(event: OutboxEvent) -> None:
    if event.event_type == 'incremental_sync_due':
        _handle_sync_due(event, mode='incremental')
        return
    if event.event_type == 'full_sync_due':
        _handle_sync_due(event, mode='full')
        return
    if event.event_type == 'full_backfill_requested':
        _handle_full_backfill_requested(event)
        return
    logger.info('Skip unsupported outbox event type=%s id=%s', event.event_type, event.id)


def _handle_sync_due(event: OutboxEvent, *, mode: str) -> None:
    from services.subscription_update.models import UpdateMode, UpdateTrigger
    from services.subscription_update.scheduler import SubscriptionScheduler

    payload = event.payload or {}
    subscription_id = int(payload['subscription_id'])
    scheduler = SubscriptionScheduler()
    trigger = UpdateTrigger.MANUAL if str(payload.get('trigger')).lower() == UpdateTrigger.MANUAL.value else UpdateTrigger.SCHEDULED
    resolved_mode = UpdateMode.FULL if mode == UpdateMode.FULL.value else UpdateMode.INCREMENTAL
    scheduler._schedule_one_direct(
        subscription_id=subscription_id,
        url=str(payload.get('url') or scheduler._get_subscription_url(subscription_id)),
        trigger=trigger,
        mode=resolved_mode,
        user_id=payload.get('user_id'),
        force=bool(payload.get('force', False)),
        trace_id=payload.get('trace_id'),
        run_id=payload.get('run_id'),
    )


def _handle_full_backfill_requested(event: OutboxEvent) -> None:
    from services import subscription_sync_state_service
    from services.subscription_update.models import UpdateMode
    from services.subscription_update.scheduler import SubscriptionScheduler

    payload = event.payload or {}
    subscription_id = int(payload['subscription_id'])
    full_state = subscription_sync_state_service.get_sync_state(subscription_id, UpdateMode.FULL.value)
    if full_state and full_state.sync_status in {'queued', 'running'}:
        return

    site = str(payload.get('site') or getattr(full_state, 'site', '') or '').strip()
    if not site and payload.get('sync_state_id'):
        source_state = subscription_sync_state_service.get_sync_state_by_id(int(payload['sync_state_id']))
        site = str(getattr(source_state, 'site', '') or '').strip()

    snapshot = _count_full_sync_pressure(site=site)
    if snapshot['global_inflight'] >= max(1, int(settings.FULL_SYNC_MAX_INFLIGHT)):
        raise RetryLaterError(int(settings.FULL_BACKFILL_RETRY_SECONDS))
    if site and snapshot['site_inflight'] >= max(1, int(settings.FULL_SYNC_SITE_MAX_INFLIGHT)):
        raise RetryLaterError(int(settings.FULL_BACKFILL_RETRY_SECONDS))

    publish_event(
        event_type='full_sync_due',
        event_key=f"full_sync_due:{subscription_id}:{payload.get('reason', 'gap')}:{datetime.now().strftime('%Y%m%d%H')}",
        aggregate_type='subscription',
        aggregate_id=str(subscription_id),
        payload={
            'subscription_id': subscription_id,
            'mode': UpdateMode.FULL.value,
            'trigger': payload.get('trigger', 'scheduled'),
            'trace_id': payload.get('trace_id'),
            'url': payload.get('url') or SubscriptionScheduler()._get_subscription_url(subscription_id),
            'site': site,
        },
        priority='low',
    )


def _count_full_sync_pressure(*, site: str) -> dict[str, int]:
    with get_session() as session:
        global_inflight = int(session.execute(
            select(func.count(SubscriptionSyncState.id)).where(
                SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                SubscriptionSyncState.sync_status.in_(['queued', 'running']),
            )
        ).scalar_one() or 0)
        site_inflight = 0
        if site:
            site_inflight = int(session.execute(
                select(func.count(SubscriptionSyncState.id)).where(
                    SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                    SubscriptionSyncState.sync_status.in_(['queued', 'running']),
                    SubscriptionSyncState.site == site,
                )
            ).scalar_one() or 0)
        event_rows = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.event_type == 'full_sync_due',
                OutboxEvent.status.in_(['pending', 'processing']),
            )
        ).scalars().all()

    for event in event_rows:
        payload = event.payload or {}
        global_inflight += 1
        if site and str(payload.get('site') or '').strip() == site:
            site_inflight += 1
    return {
        'global_inflight': global_inflight,
        'site_inflight': site_inflight,
    }


def _mark_event_failed(*, event_id: int, error_message: str, now: datetime) -> None:
    with get_session() as session:
        event = session.get(OutboxEvent, event_id)
        if not event:
            return
        event.attempt_count += 1
        event.last_error = error_message
        event.locked_by = None
        event.locked_at = None
        if event.attempt_count >= event.max_attempts:
            event.status = 'dead'
            event.processed_at = now
        else:
            event.status = 'pending'
            event.available_at = now + timedelta(seconds=min(30 * event.attempt_count, 300))
        session.flush()


def _reschedule_event(*, event_id: int, delay_seconds: int, now: datetime) -> None:
    with get_session() as session:
        event = session.get(OutboxEvent, event_id)
        if not event:
            return
        event.status = 'pending'
        event.locked_by = None
        event.locked_at = None
        event.available_at = now + timedelta(seconds=max(1, delay_seconds))
        session.flush()


def _notify_new_event(session, *, event_type: str) -> None:
    bind = session.get_bind()
    if bind is None or bind.dialect.name != 'postgresql':
        return
    session.execute(select(func.pg_notify(settings.OUTBOX_NOTIFY_CHANNEL, event_type)))


def create_listener_stop_event() -> Event:
    return Event()


def run_notification_listener(stop_event: Event) -> None:
    timeout = max(1, int(settings.OUTBOX_NOTIFY_POLL_TIMEOUT_SECONDS))
    batch_size = max(1, int(settings.OUTBOX_CONSUME_BATCH_SIZE))
    if engine.dialect.name != 'postgresql':
        while not stop_event.is_set():
            stop_event.wait(timeout)
            if stop_event.is_set():
                break
            consume_available_events(limit=batch_size, worker_id='scheduler-listener')
        return

    while not stop_event.is_set():
        raw_conn = None
        cursor = None
        try:
            raw_conn = engine.raw_connection()
            raw_conn.set_session(autocommit=True)
            cursor = raw_conn.cursor()
            cursor.execute(f'LISTEN {settings.OUTBOX_NOTIFY_CHANNEL};')
            while not stop_event.is_set():
                ready, _, _ = io_select.select([raw_conn], [], [], timeout)
                if ready:
                    raw_conn.poll()
                    while raw_conn.notifies:
                        raw_conn.notifies.pop(0)
                        consume_available_events(limit=batch_size, worker_id='scheduler-listener')
                    continue
                consume_available_events(limit=batch_size, worker_id='scheduler-listener')
        except Exception:
            logger.exception('Outbox notification listener failed; retrying')
            stop_event.wait(1)
        finally:
            if cursor is not None:
                cursor.close()
            if raw_conn is not None:
                raw_conn.close()
