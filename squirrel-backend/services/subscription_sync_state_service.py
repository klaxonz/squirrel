from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import exists, select, update

from core.cache import redis_client
from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from services.crawl_tasks import service as crawl_task_service
from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncPhase, SyncRunStatus, create_run
from utils import url_helper


INCREMENTAL_INTERVAL = timedelta(minutes=5)
FULL_INTERVAL = timedelta(hours=2)
INCREMENTAL_PENDING_THRESHOLD = 15
RUNNING_TIMEOUT = timedelta(minutes=30)
QUEUED_RECOVERY_GRACE = timedelta(minutes=2)
SYNC_BATCH_SIZE = 200
MAX_DRAIN_BATCHES = 20


def get_mode_interval(mode: str) -> timedelta:
    if mode == SyncMode.FULL.value:
        return FULL_INTERVAL
    return INCREMENTAL_INTERVAL


def build_retry_delay(mode: str, failure_count: int) -> timedelta:
    if mode == SyncMode.FULL.value:
        minutes = min(30 * (2 ** max(failure_count - 1, 0)), 24 * 60)
        return timedelta(minutes=minutes)
    minutes = min(5 * (2 ** max(failure_count - 1, 0)), 6 * 60)
    return timedelta(minutes=minutes)


def build_success_delay(mode: str, idle_sync_count: int, videos_found: int) -> timedelta:
    if mode == SyncMode.FULL.value:
        if videos_found > 0:
            return FULL_INTERVAL
        minutes = min(int(FULL_INTERVAL.total_seconds() / 60) * (2 ** min(idle_sync_count, 3)), 24 * 60)
        return timedelta(minutes=minutes)

    if videos_found > 0:
        return INCREMENTAL_INTERVAL
    base_minutes = 15
    minutes = min(base_minutes * (2 ** min(idle_sync_count, 4)), 6 * 60)
    return timedelta(minutes=minutes)


def _resolve_site(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        return url_helper.extract_top_level_domain(url)
    except Exception:
        return None


def _get_or_create_sync_state_in_session(
    session,
    subscription_id: int,
    mode: str,
    url: Optional[str],
) -> SubscriptionSyncState:
    state = session.execute(
        select(SubscriptionSyncState).where(
            SubscriptionSyncState.subscription_id == subscription_id,
            SubscriptionSyncState.sync_mode == mode,
        )
    ).scalar_one_or_none()
    if state:
        if not state.site:
            state.site = _resolve_site(url)
        if state.next_sync_at is None:
            state.next_sync_at = datetime.now()
        return state

    state = SubscriptionSyncState(
        subscription_id=subscription_id,
        site=_resolve_site(url),
        sync_mode=mode,
        sync_status=SyncStatus.IDLE.value,
        cursor_payload={},
        next_sync_at=datetime.now(),
    )
    session.add(state)
    session.flush()
    return state


def ensure_sync_states(subscription_id: int, url: Optional[str]) -> dict[str, SubscriptionSyncState]:
    with get_session() as session:
        states = {
            SyncMode.INCREMENTAL.value: _get_or_create_sync_state_in_session(
                session, subscription_id, SyncMode.INCREMENTAL.value, url
            ),
            SyncMode.FULL.value: _get_or_create_sync_state_in_session(
                session, subscription_id, SyncMode.FULL.value, url
            ),
        }
        return states


def ensure_incremental_sync_state(subscription_id: int, url: Optional[str]) -> SubscriptionSyncState:
    with get_session() as session:
        return _get_or_create_sync_state_in_session(session, subscription_id, SyncMode.INCREMENTAL.value, url)


def deactivate_sync_states(subscription_id: int, *, reason: str = 'deactivated') -> int:
    now = datetime.now()
    updated_count = 0

    with get_session() as session:
        states = session.execute(
            select(SubscriptionSyncState).where(
                SubscriptionSyncState.subscription_id == subscription_id,
            )
        ).scalars().all()

        for state in states:
            state.sync_status = SyncStatus.IDLE.value
            state.last_error = reason
            state.queue_token = None
            state.queued_at = None
            state.locked_at = None
            state.pending_video_count = 0
            state.last_sync_at = now
            state.version += 1
            updated_count += 1

    return updated_count


def prepare_sync_state_for_enqueue(
    subscription_id: int,
    url: Optional[str],
    mode: str,
    *,
    scheduled: bool,
) -> tuple[Optional[SubscriptionSyncState], str]:
    now = datetime.now()
    with get_session() as session:
        state = _get_or_create_sync_state_in_session(session, subscription_id, mode, url)
        _recover_stale_running_state(state, now)

        if state.sync_status == SyncStatus.RUNNING.value:
            return state, 'in_progress'
        if state.sync_status == SyncStatus.QUEUED.value:
            return state, 'queued'

        if scheduled and has_incremental_backpressure(state):
            state.sync_status = SyncStatus.SUCCESS.value
            state.last_sync_at = now
            state.last_error = 'queue_backpressure'
            state.queue_token = None
            state.queued_at = None
            state.locked_at = None
            state.next_sync_at = now + get_mode_interval(state.sync_mode)
            state.version += 1
            return state, 'deferred'

        return state, 'ready'


def get_sync_state(subscription_id: int, mode: str) -> Optional[SubscriptionSyncState]:
    with get_session() as session:
        return session.execute(
            select(SubscriptionSyncState).where(
                SubscriptionSyncState.subscription_id == subscription_id,
                SubscriptionSyncState.sync_mode == mode,
            )
        ).scalar_one_or_none()


def get_sync_state_by_id(sync_state_id: int) -> Optional[SubscriptionSyncState]:
    with get_session() as session:
        return session.get(SubscriptionSyncState, sync_state_id)


def list_due_sync_states(mode: str, limit: int = SYNC_BATCH_SIZE) -> list[tuple[SubscriptionSyncState, str]]:
    now = datetime.now()
    with get_session() as session:
        _recover_stale_running_states_in_session(session, now)
        rows = session.execute(
            select(SubscriptionSyncState, Subscription.url)
            .join(Subscription, Subscription.id == SubscriptionSyncState.subscription_id)
            .where(
                Subscription.is_deleted.is_(False),
                SubscriptionSyncState.sync_mode == mode,
                SubscriptionSyncState.next_sync_at <= now,
                SubscriptionSyncState.sync_status.in_(
                    [
                        SyncStatus.IDLE.value,
                        SyncStatus.SUCCESS.value,
                        SyncStatus.FAILED.value,
                    ]
                ),
                exists(
                    select(1).select_from(UserSubscription).where(
                        UserSubscription.subscription_id == Subscription.id,
                        UserSubscription.is_deleted.is_(False),
                    )
                ),
            )
            .order_by(SubscriptionSyncState.next_sync_at.asc(), SubscriptionSyncState.id.asc())
            .limit(limit)
        ).all()
        return [(row[0], row[1]) for row in rows]


def _recover_stale_running_states_in_session(session, now: datetime) -> None:
    stale_before = now - RUNNING_TIMEOUT
    states = session.execute(
        select(SubscriptionSyncState).where(
            SubscriptionSyncState.sync_status == SyncStatus.RUNNING.value,
            SubscriptionSyncState.locked_at.is_not(None),
            SubscriptionSyncState.locked_at <= stale_before,
        )
    ).scalars().all()
    for state in states:
        _recover_stale_running_state(state, now)


def _recover_stale_running_state(state: SubscriptionSyncState, now: datetime) -> None:
    state.sync_status = SyncStatus.FAILED.value
    state.last_error = 'stale_running_timeout'
    state.queue_token = None
    state.queued_at = None
    state.locked_at = None
    state.failure_count += 1
    state.next_sync_at = now
    state.version += 1


def _append_recovery_run_events(
    session,
    *,
    state: SubscriptionSyncState,
    event_type: str,
    event_phase: str,
    event_status: str,
    reason: str,
    occurred_at: datetime,
) -> None:
    run_context = create_run(
        subscription_id=state.subscription_id,
        sync_state_id=state.id,
        site=state.site,
        sync_mode=state.sync_mode,
        trigger='system',
        occurred_at=occurred_at,
    )
    append_event(
        SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=state.subscription_id,
            sync_state_id=state.id,
            site=state.site,
            sync_mode=state.sync_mode,
            trigger='system',
            event_type=SyncEventType.RUN_CREATED,
            event_phase=SyncPhase.INIT,
            event_status=SyncRunStatus.CREATED,
            payload={'pending_video_count': state.pending_video_count},
            occurred_at=occurred_at,
        ),
        session=session,
    )
    append_event(
        SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=state.subscription_id,
            sync_state_id=state.id,
            site=state.site,
            sync_mode=state.sync_mode,
            trigger='system',
            event_type=event_type,
            event_phase=event_phase,
            event_status=event_status,
            payload={
                'reason': reason,
                'error_message': reason,
                'pending_video_count': state.pending_video_count,
                'next_sync_at': state.next_sync_at,
            },
            message=reason,
            occurred_at=occurred_at,
        ),
        session=session,
    )


def recover_stale_sync_state(sync_state_id: int) -> Optional[SubscriptionSyncState]:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        if state.sync_status != SyncStatus.RUNNING.value or not state.locked_at:
            return state
        if state.locked_at > now - RUNNING_TIMEOUT:
            return state
        _recover_stale_running_state(state, now)
        _append_recovery_run_events(
            session,
            state=state,
            event_type=SyncEventType.STALE_RUNNING_RECOVERED,
            event_phase=SyncPhase.FAILED,
            event_status=SyncRunStatus.TIMEOUT,
            reason='stale_running_timeout',
            occurred_at=now,
        )
        return state


def queue_sync_state(sync_state_id: int, queue_token: str) -> Optional[SubscriptionSyncState]:
    now = datetime.now()
    with get_session() as session:
        session.execute(
            update(SubscriptionSyncState)
            .where(
                SubscriptionSyncState.id == sync_state_id,
                SubscriptionSyncState.sync_status.notin_(
                    [SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]
                ),
            )
            .values(
                sync_status=SyncStatus.QUEUED.value,
                queue_token=queue_token,
                queued_at=now,
                locked_at=None,
                last_error=None,
                version=SubscriptionSyncState.version + 1,
            )
        )
        return session.execute(
            select(SubscriptionSyncState).where(SubscriptionSyncState.id == sync_state_id)
        ).scalar_one_or_none()
def _append_state_event(
    session,
    *,
    state: SubscriptionSyncState,
    run_id: Optional[str],
    request_id: Optional[str],
    trace_id: Optional[str],
    trigger: Optional[str],
    event_type: str,
    event_phase: Optional[str],
    event_status: Optional[str],
    payload: Optional[dict] = None,
    message: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
) -> None:
    if not run_id:
        return
    append_event(
        SyncEventInput(
            stream_id=run_id,
            subscription_id=state.subscription_id,
            sync_state_id=state.id,
            site=state.site,
            sync_mode=state.sync_mode,
            trigger=trigger,
            request_id=request_id,
            trace_id=trace_id,
            event_type=event_type,
            event_phase=event_phase,
            event_status=event_status,
            payload=payload,
            message=message,
            occurred_at=occurred_at,
        ),
        session=session,
    )


def _complete_sync_success_in_session(
    session,
    *,
    state: SubscriptionSyncState,
    source_video_count: Optional[int] = None,
    videos_found: int = 0,
    videos_enqueued: int = 0,
    next_sync_at: Optional[datetime] = None,
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger: Optional[str] = None,
) -> SubscriptionSyncState:
    now = datetime.now()
    started_at = state.locked_at or state.last_sync_at
    state.sync_status = SyncStatus.SUCCESS.value
    state.last_sync_at = now
    state.last_success_at = now
    state.queue_token = None
    state.queued_at = None
    state.locked_at = None
    state.failure_count = 0
    state.last_error = None
    state.idle_sync_count = 0 if videos_found > 0 else state.idle_sync_count + 1
    state.next_sync_at = next_sync_at or (now + build_success_delay(state.sync_mode, state.idle_sync_count, videos_found))
    state.version += 1
    _append_state_event(
        session,
        state=state,
        run_id=run_id,
        request_id=request_id,
        trace_id=trace_id,
        trigger=trigger,
        event_type=SyncEventType.COMPLETED,
        event_phase=SyncPhase.COMPLETED,
        event_status=SyncRunStatus.SUCCESS,
        payload={
            'cursor_payload': state.cursor_payload,
            'latest_video_url': state.last_seen_video_url,
            'source_video_count': source_video_count,
            'videos_found': videos_found,
            'videos_enqueued': videos_enqueued,
            'pending_video_count': state.pending_video_count,
            'failure_count': state.failure_count,
            'next_sync_at': state.next_sync_at,
            'duration_ms': int((now - started_at).total_seconds() * 1000) if started_at else 0,
        },
        occurred_at=now,
    )
    return state


def claim_sync_state(
    sync_state_id: int,
    queue_token: str,
    *,
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger: Optional[str] = None,
) -> Optional[SubscriptionSyncState]:
    now = datetime.now()
    with get_session() as session:
        result = session.execute(
            update(SubscriptionSyncState)
            .where(
                SubscriptionSyncState.id == sync_state_id,
                SubscriptionSyncState.sync_status == SyncStatus.QUEUED.value,
                SubscriptionSyncState.queue_token == queue_token,
            )
            .values(
                sync_status=SyncStatus.RUNNING.value,
                locked_at=now,
                last_sync_at=now,
                version=SubscriptionSyncState.version + 1,
            )
        )
        if result.rowcount == 0:
            return None
        state = session.execute(
            select(SubscriptionSyncState).where(SubscriptionSyncState.id == sync_state_id)
        ).scalar_one_or_none()
        if not state:
            return None
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=SyncEventType.CLAIMED,
            event_phase=SyncPhase.CLAIMED,
            event_status=SyncRunStatus.RUNNING,
            payload={
                'pending_video_count': state.pending_video_count,
                'queue_token': queue_token,
            },
            occurred_at=now,
        )
        return state


def reconcile_task_retry_state(
    sync_state_id: Optional[int],
    queue_token: Optional[str],
    *,
    now: Optional[datetime] = None,
    retryable: bool,
    error_message: Optional[str] = None,
) -> Optional[SubscriptionSyncState]:
    if not sync_state_id:
        return None

    now = now or datetime.now()
    expected_token = str(queue_token or '').strip() or None

    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None

        current_token = str(state.queue_token or '').strip() or None
        if expected_token and current_token and current_token != expected_token:
            return state

        if retryable:
            if state.sync_status not in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}:
                return state
            state.sync_status = SyncStatus.QUEUED.value
            state.queue_token = expected_token or state.queue_token
            state.queued_at = now
            state.locked_at = None
            state.last_error = error_message
            state.version += 1
            return state

        if state.sync_status not in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}:
            return state

        state.failure_count += 1
        state.sync_status = SyncStatus.FAILED.value
        state.last_sync_at = now
        state.last_error = error_message or 'task_retry_exhausted'
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.idle_sync_count = 0
        state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
        state.version += 1
        return state


def continue_full_sync_batch(
    sync_state_id: int,
    *,
    cursor_payload: Optional[dict],
    latest_video_url: Optional[str],
    source_video_count: Optional[int] = None,
    videos_found: int = 0,
    videos_enqueued: int = 0,
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger: Optional[str] = None,
) -> Optional[SubscriptionSyncState]:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        state.sync_status = SyncStatus.SUCCESS.value
        state.cursor_payload = cursor_payload or {}
        if latest_video_url and not state.last_seen_video_url:
            state.last_seen_video_url = latest_video_url
        state.last_sync_at = now
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.failure_count = 0
        state.idle_sync_count = 0
        state.last_error = None
        state.next_sync_at = now
        state.version += 1
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=SyncEventType.CONTINUED,
            event_phase=SyncPhase.FINALIZING,
            event_status=SyncRunStatus.RUNNING,
            payload={
                'cursor_payload': state.cursor_payload,
                'latest_video_url': latest_video_url,
                'source_video_count': source_video_count,
                'videos_found_delta': videos_found,
                'videos_enqueued_delta': videos_enqueued,
                'pending_video_count': state.pending_video_count,
                'next_sync_at': state.next_sync_at,
                'has_more': True,
            },
            occurred_at=now,
        )
        return state


def mark_sync_success(
    sync_state_id: int,
    *,
    cursor_payload: Optional[dict],
    latest_video_url: Optional[str],
    source_video_count: Optional[int] = None,
    videos_found: int = 0,
    videos_enqueued: int = 0,
    next_sync_at: Optional[datetime] = None,
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger: Optional[str] = None,
) -> Optional[SubscriptionSyncState]:
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        now = datetime.now()
        if cursor_payload is not None:
            state.cursor_payload = cursor_payload
        if latest_video_url:
            state.last_seen_video_url = latest_video_url

        if state.pending_video_count > 0:
            state.sync_status = SyncStatus.RUNNING.value
            state.last_sync_at = now
            state.queue_token = None
            state.queued_at = None
            state.locked_at = None
            state.failure_count = 0
            state.last_error = None
            state.version += 1
            _append_state_event(
                session,
                state=state,
                run_id=run_id,
                request_id=request_id,
                trace_id=trace_id,
                trigger=trigger,
                event_type=SyncEventType.PHASE_CHANGED,
                event_phase=SyncPhase.EXTRACTING,
                event_status=SyncRunStatus.RUNNING,
                payload={
                    'cursor_payload': state.cursor_payload,
                    'latest_video_url': state.last_seen_video_url,
                    'source_video_count': source_video_count,
                    'videos_found': videos_found,
                    'videos_enqueued': videos_enqueued,
                    'pending_video_count': state.pending_video_count,
                    'feed_completed': True,
                },
                occurred_at=now,
            )
            return state

        _complete_sync_success_in_session(
            session,
            state=state,
            source_video_count=source_video_count,
            videos_found=videos_found,
            videos_enqueued=videos_enqueued,
            next_sync_at=next_sync_at,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
        )
        return state


def mark_sync_skipped(
    sync_state_id: int,
    *,
    next_sync_at: Optional[datetime] = None,
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger: Optional[str] = None,
    reason: Optional[str] = None,
    event_type: str = SyncEventType.DEFERRED,
    event_phase: str = SyncPhase.DEFERRED,
    event_status: str = SyncRunStatus.DEFERRED,
) -> Optional[SubscriptionSyncState]:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        state.sync_status = SyncStatus.SUCCESS.value
        state.last_sync_at = now
        state.last_error = None
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.failure_count = 0
        state.next_sync_at = next_sync_at or (now + get_mode_interval(state.sync_mode))
        state.version += 1
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=event_type,
            event_phase=event_phase,
            event_status=event_status,
            payload={
                'reason': reason,
                'next_sync_at': state.next_sync_at,
                'pending_video_count': state.pending_video_count,
            },
            message=reason,
            occurred_at=now,
        )
        return state


def mark_sync_failed(
    sync_state_id: int,
    error_message: str,
    *,
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    error_type: Optional[str] = None,
    trigger: Optional[str] = None,
) -> Optional[SubscriptionSyncState]:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        started_at = state.locked_at
        state.failure_count += 1
        state.sync_status = SyncStatus.FAILED.value
        state.last_sync_at = now
        state.last_error = error_message
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.idle_sync_count = 0
        state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
        state.version += 1
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=SyncEventType.FAILED,
            event_phase=SyncPhase.FAILED,
            event_status=SyncRunStatus.FAILED,
            payload={
                'error_type': error_type or 'sync_failed',
                'error_message': error_message,
                'failure_count': state.failure_count,
                'pending_video_count': state.pending_video_count,
                'next_sync_at': state.next_sync_at,
                'duration_ms': int((now - started_at).total_seconds() * 1000) if started_at else 0,
            },
            message=error_message,
            occurred_at=now,
        )
        return state


def defer_sync_state(
    sync_state_id: int,
    *,
    delay: timedelta,
    error_message: Optional[str] = None,
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger: Optional[str] = None,
) -> Optional[SubscriptionSyncState]:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        state.sync_status = SyncStatus.SUCCESS.value
        state.last_sync_at = now
        state.last_error = error_message
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.idle_sync_count = 0
        state.next_sync_at = now + delay
        state.version += 1
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=SyncEventType.DEFERRED,
            event_phase=SyncPhase.DEFERRED,
            event_status=SyncRunStatus.DEFERRED,
            payload={
                'error_message': error_message,
                'pending_video_count': state.pending_video_count,
                'next_sync_at': state.next_sync_at,
            },
            message=error_message,
            occurred_at=now,
        )
        return state


def increment_pending_video_count(sync_state_id: Optional[int], count: int = 1) -> None:
    if not sync_state_id or count <= 0:
        return
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return
        state.pending_video_count += count
        state.version += 1


def decrement_pending_video_count(
    sync_state_id: Optional[int],
    count: int = 1,
    *,
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger: Optional[str] = None,
) -> None:
    if not sync_state_id or count <= 0:
        return
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return
        state.pending_video_count = max(0, state.pending_video_count - count)
        state.version += 1
        if state.pending_video_count == 0 and state.sync_status == SyncStatus.RUNNING.value and state.locked_at is None:
            _complete_sync_success_in_session(
                session,
                state=state,
                run_id=run_id,
                request_id=request_id,
                trace_id=trace_id,
                trigger=trigger,
            )


def build_queue_token() -> str:
    return uuid4().hex


def has_incremental_backpressure(sync_state: SubscriptionSyncState) -> bool:
    return sync_state.sync_mode == SyncMode.INCREMENTAL.value and sync_state.pending_video_count >= INCREMENTAL_PENDING_THRESHOLD


def reconcile_pending_video_counts() -> dict[str, int]:
    counts = _scan_pending_video_counts()
    with get_session() as session:
        session.execute(
            update(SubscriptionSyncState)
            .where(SubscriptionSyncState.pending_video_count != 0)
            .values(pending_video_count=0)
        )
        for sync_state_id, pending_count in counts.items():
            session.execute(
                update(SubscriptionSyncState)
                .where(SubscriptionSyncState.id == sync_state_id)
                .values(pending_video_count=pending_count)
            )
    return {
        'states': len(counts),
        'videos': sum(counts.values()),
    }


def recover_stale_queued_sync_states(grace: timedelta = QUEUED_RECOVERY_GRACE) -> dict[str, int]:
    active_sync_state_ids = _scan_subscription_update_state_ids()
    now = datetime.now()
    recovered = 0

    with get_session() as session:
        queued_states = session.execute(
            select(SubscriptionSyncState).where(
                SubscriptionSyncState.sync_status == SyncStatus.QUEUED.value,
                SubscriptionSyncState.queued_at.is_not(None),
                SubscriptionSyncState.queued_at <= now - grace,
            )
        ).scalars().all()

        for state in queued_states:
            if state.id in active_sync_state_ids:
                continue
            state.sync_status = SyncStatus.FAILED.value
            state.last_sync_at = now
            state.last_error = 'stale_queued_missing_message'
            state.queue_token = None
            state.queued_at = None
            state.locked_at = None
            state.next_sync_at = now
            state.version += 1
            _append_recovery_run_events(
                session,
                state=state,
                event_type=SyncEventType.STALE_QUEUED_RECOVERED,
                event_phase=SyncPhase.FAILED,
                event_status=SyncRunStatus.FAILED,
                reason='stale_queued_missing_message',
                occurred_at=now,
            )
            recovered += 1

    return {
        'queued_states': len(queued_states),
        'recovered': recovered,
    }


def recover_stale_running_sync_states(timeout: timedelta = RUNNING_TIMEOUT) -> dict[str, int]:
    now = datetime.now()
    recovered = 0

    with get_session() as session:
        stale_before = now - timeout
        states = session.execute(
            select(SubscriptionSyncState).where(
                SubscriptionSyncState.sync_status == SyncStatus.RUNNING.value,
                SubscriptionSyncState.locked_at.is_not(None),
                SubscriptionSyncState.locked_at <= stale_before,
            )
        ).scalars().all()

        for state in states:
            _recover_stale_running_state(state, now)
            _append_recovery_run_events(
                session,
                state=state,
                event_type=SyncEventType.STALE_RUNNING_RECOVERED,
                event_phase=SyncPhase.FAILED,
                event_status=SyncRunStatus.TIMEOUT,
                reason='stale_running_timeout',
                occurred_at=now,
            )
            recovered += 1

    return {
        'running_states': len(states),
        'recovered': recovered,
    }


def _scan_pending_video_counts() -> dict[int, int]:
    return crawl_task_service.count_pending_video_tasks_by_sync_state()


def _scan_subscription_update_state_ids() -> set[int]:
    return crawl_task_service.list_active_subscription_sync_state_ids()


def attach_sync_fields(target: dict, sync_state: Optional[SubscriptionSyncState]) -> dict:
    if not sync_state:
        target.setdefault('sync_status', SyncStatus.IDLE.value)
        target.setdefault('last_sync_at', '')
        target.setdefault('last_success_at', '')
        target.setdefault('next_sync_at', '')
        target.setdefault('last_error', '')
        target.setdefault('pending_video_count', 0)
        return target

    target['sync_status'] = sync_state.sync_status
    target['last_sync_at'] = sync_state.last_sync_at.strftime('%Y-%m-%d %H:%M:%S') if sync_state.last_sync_at else ''
    target['last_success_at'] = sync_state.last_success_at.strftime('%Y-%m-%d %H:%M:%S') if sync_state.last_success_at else ''
    target['next_sync_at'] = sync_state.next_sync_at.strftime('%Y-%m-%d %H:%M:%S') if sync_state.next_sync_at else ''
    target['last_error'] = sync_state.last_error or ''
    target['pending_video_count'] = sync_state.pending_video_count
    return target
