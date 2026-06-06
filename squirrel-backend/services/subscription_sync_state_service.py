from __future__ import annotations
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import exists, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.cache import redis_client
from core.database import get_session
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from services.crawl_tasks import service as crawl_task_service
from services.crawl_tasks.task_types import subscription_sync_task_types
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
    except (ValueError, TypeError):
        return None


def _fingerprint_head_sample(urls: Optional[list[str]]) -> Optional[str]:
    normalized = [str(url).strip() for url in (urls or []) if str(url).strip()]
    if not normalized:
        return None
    payload = '\n'.join(normalized[:20]).encode('utf-8')
    return hashlib.sha1(payload).hexdigest()


def _calculate_head_overlap(previous_urls: Optional[list[str]], current_urls: Optional[list[str]]) -> Optional[float]:
    previous = {str(url).strip() for url in (previous_urls or []) if str(url).strip()}
    current = {str(url).strip() for url in (current_urls or []) if str(url).strip()}
    if not previous or not current:
        return None
    overlap = len(previous & current)
    return overlap / max(1, min(len(previous), len(current)))


def _get_or_create_sync_state_in_session(
    session: Session,
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


def list_due_sync_states(
    mode: str,
    limit: int = SYNC_BATCH_SIZE,
    *,
    now: Optional[datetime] = None,
) -> list[tuple[SubscriptionSyncState, str]]:
    now = now or datetime.now()
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


def _recover_stale_running_states_in_session(session: Session, now: datetime) -> None:
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
    session: Session,
    *,
    state: SubscriptionSyncState,
    event_type: str,
    event_phase: str,
    event_status: str,
    reason: str,
    occurred_at: datetime,
) -> None:
    run_projection = _get_latest_state_run_projection(session, state)
    if run_projection:
        _append_state_event(
            session,
            state=state,
            run_id=run_projection.run_id,
            request_id=run_projection.request_id,
            trace_id=run_projection.trace_id,
            trigger=run_projection.trigger or 'system',
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
        )
        return

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


def _append_terminal_reconcile_run_events(
    session: Session,
    *,
    state: SubscriptionSyncState,
    event_type: str,
    event_phase: str,
    event_status: str,
    reason: str,
    error_message: Optional[str],
    occurred_at: datetime,
) -> None:
    run_projection = _get_latest_state_run_projection(session, state)
    if run_projection:
        started_at = run_projection.started_at or state.locked_at or state.last_sync_at
        _append_state_event(
            session,
            state=state,
            run_id=run_projection.run_id,
            request_id=run_projection.request_id,
            trace_id=run_projection.trace_id,
            trigger=run_projection.trigger or 'system',
            event_type=event_type,
            event_phase=event_phase,
            event_status=event_status,
            payload={
                'reason': reason,
                'error_message': error_message,
                'failure_count': state.failure_count,
                'pending_video_count': state.pending_video_count,
                'next_sync_at': state.next_sync_at,
                'duration_ms': int((occurred_at - started_at).total_seconds() * 1000) if started_at else 0,
            },
            message=error_message or reason,
            occurred_at=occurred_at,
        )
        return

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

    started_at = state.locked_at or state.last_sync_at
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
                'error_message': error_message,
                'failure_count': state.failure_count,
                'pending_video_count': state.pending_video_count,
                'next_sync_at': state.next_sync_at,
                'duration_ms': int((occurred_at - started_at).total_seconds() * 1000) if started_at else 0,
            },
            message=error_message or reason,
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
    session: Session,
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
    session: Session,
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
    if state.sync_mode == SyncMode.FULL.value:
        state.gap_suspicion_score = 0
        state.gap_suspicion_reason = None
        state.last_gap_detected_at = None
        state.head_anchor_missing_count = 0
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
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    trigger: Optional[str] = None,
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
            _append_state_event(
                session,
                state=state,
                run_id=run_id,
                request_id=request_id,
                trace_id=trace_id,
                trigger=trigger,
                event_type=SyncEventType.QUEUED,
                event_phase=SyncPhase.QUEUED,
                event_status=SyncRunStatus.QUEUED,
                payload={
                    'queue_token': state.queue_token,
                    'queued_at': state.queued_at,
                    'pending_video_count': state.pending_video_count,
                    'error_message': error_message,
                },
                message=error_message,
                occurred_at=now,
            )
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
                'error_message': state.last_error,
                'failure_count': state.failure_count,
                'pending_video_count': state.pending_video_count,
                'next_sync_at': state.next_sync_at,
            },
            message=state.last_error,
            occurred_at=now,
        )
        return state


def reconcile_retry_wait_run_projections() -> dict[str, int]:
    scanned = 0
    repaired = 0
    now = datetime.now()
    feed_phase_candidates = {
        SyncPhase.FETCHING_FEED,
        SyncPhase.CALCULATING_DELTA,
        SyncPhase.ENQUEUEING,
    }

    with get_session() as session:
        rows = session.execute(
            select(
                SubscriptionSyncSubscriptionProjection,
                SubscriptionSyncRunProjection,
                SubscriptionSyncState,
            )
            .join(
                SubscriptionSyncRunProjection,
                SubscriptionSyncRunProjection.run_id == SubscriptionSyncSubscriptionProjection.latest_run_id,
            )
            .join(
                SubscriptionSyncState,
                SubscriptionSyncState.id == SubscriptionSyncRunProjection.sync_state_id,
            )
            .where(
                SubscriptionSyncSubscriptionProjection.current_status == SyncRunStatus.RUNNING,
                SubscriptionSyncState.sync_status == SyncStatus.QUEUED.value,
                SubscriptionSyncRunProjection.current_phase.in_(feed_phase_candidates),
            )
        ).all()

        subscription_ids = {
            state.subscription_id
            for _, _, state in rows
            if state.subscription_id is not None
        }
        if not subscription_ids:
            return {
                'candidates': 0,
                'repaired': 0,
            }

        tasks = session.execute(
            select(CrawlTask)
            .where(
                CrawlTask.task_type.in_(subscription_sync_task_types()),
                CrawlTask.status == 'retry_wait',
                CrawlTask.last_error == 'lease_expired',
                CrawlTask.subscription_id.in_(subscription_ids),
            )
            .order_by(CrawlTask.id.desc())
        ).scalars().all()

        latest_task_by_sync_state: dict[int, CrawlTask] = {}
        for task in tasks:
            sync_state_id = (task.payload or {}).get('sync_state_id')
            try:
                sync_state_id = int(sync_state_id)
            except (TypeError, ValueError):
                continue
            latest_task_by_sync_state.setdefault(sync_state_id, task)

        for _, run_projection, state in rows:
            scanned += 1
            task = latest_task_by_sync_state.get(state.id)
            if not task:
                continue

            task_payload = task.payload or {}
            task_run_id = str(task_payload.get('run_id') or '').strip() or None
            if task_run_id and task_run_id != run_projection.run_id:
                continue
            error_message = str(task.last_error or state.last_error or '').strip()
            occurred_at = state.queued_at or task.updated_at or now
            _append_state_event(
                session,
                state=state,
                run_id=run_projection.run_id,
                request_id=run_projection.request_id,
                trace_id=run_projection.trace_id,
                trigger=run_projection.trigger,
                event_type=SyncEventType.QUEUED,
                event_phase=SyncPhase.QUEUED,
                event_status=SyncRunStatus.QUEUED,
                payload={
                    'queue_token': state.queue_token or task_payload.get('queue_token'),
                    'queued_at': occurred_at,
                    'pending_video_count': state.pending_video_count,
                    'error_message': error_message,
                },
                message=error_message,
                occurred_at=occurred_at,
            )
            repaired += 1

    return {
        'candidates': scanned,
        'repaired': repaired,
    }


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


def record_gap_observation(
    sync_state_id: int,
    *,
    head_sample_urls: Optional[list[str]],
    anchor_found: Optional[bool],
    cursor_invalid: bool,
    cursor_loop_detected: bool,
    total_available: Optional[int],
    local_total: Optional[int],
    now: Optional[datetime] = None,
    trigger: str = 'scheduled',
    trace_id: Optional[str] = None,
) -> dict[str, int | bool]:
    from services import outbox_event_service

    current_time = now or datetime.now()
    emitted_full_request = False

    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return {'gap_suspicion_score': 0, 'emitted_full_request': False}

        previous_head_sample = list(state.last_head_sample_urls or [])
        score = int(state.gap_suspicion_score or 0)
        reasons: list[str] = []

        if anchor_found is False:
            score += 5
            state.head_anchor_missing_count += 1
            reasons.append('anchor_missing')
        elif anchor_found is True:
            score = max(0, score - 4)
            state.head_anchor_missing_count = 0

        if cursor_invalid:
            score += 5
            reasons.append('cursor_invalid')

        if cursor_loop_detected:
            score += 5
            reasons.append('cursor_loop_detected')

        overlap = _calculate_head_overlap(previous_head_sample, head_sample_urls)
        if overlap is not None and overlap < 0.3:
            score += 3
            reasons.append('low_head_overlap')
        elif overlap is not None and overlap >= 0.6:
            score = max(0, score - 2)

        if total_available is not None and local_total is not None:
            drift = max(0, int(total_available) - int(local_total))
            if drift > max(20, int(local_total * 0.1)):
                score += 2
                reasons.append('total_drift')

        if state.head_anchor_missing_count >= 2 and anchor_found is False:
            score += 2
            reasons.append('repeated_anchor_missing')

        state.last_head_sample_urls = list(head_sample_urls or [])
        state.last_head_fingerprint = _fingerprint_head_sample(head_sample_urls)
        state.last_known_total_available = total_available
        state.gap_suspicion_score = max(0, score)
        state.gap_suspicion_reason = ','.join(reasons) if reasons else None
        if reasons:
            state.last_gap_detected_at = current_time
        state.version += 1

        should_request_full = (
            state.sync_mode == SyncMode.INCREMENTAL.value
            and state.gap_suspicion_score >= 8
            and (
                state.last_full_requested_at is None
                or state.last_full_requested_at <= current_time - timedelta(hours=24)
            )
        )
        if should_request_full:
            outbox_event_service.publish_event(
                event_type='full_backfill_requested',
                event_key=f'full_backfill_requested:{state.subscription_id}:{current_time.strftime("%Y%m%d")}:{state.gap_suspicion_score}',
                aggregate_type='subscription',
                aggregate_id=str(state.subscription_id),
                payload={
                    'subscription_id': state.subscription_id,
                    'sync_state_id': state.id,
                    'site': state.site,
                    'trigger': trigger,
                    'trace_id': trace_id,
                    'reason': state.gap_suspicion_reason or 'gap_suspicion',
                },
                priority='normal',
                available_at=current_time,
            )
            state.last_full_requested_at = current_time
            emitted_full_request = True

        return {
            'gap_suspicion_score': int(state.gap_suspicion_score),
            'emitted_full_request': emitted_full_request,
        }


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
    allow_completion: bool = True,
) -> None:
    if not sync_state_id or count <= 0:
        return
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return
        state.pending_video_count = max(0, state.pending_video_count - count)
        state.version += 1
        if (
            allow_completion
            and state.pending_video_count == 0
            and state.sync_status == SyncStatus.RUNNING.value
            and state.locked_at is None
            and _can_complete_drained_state(state.id)
        ):
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


def reconcile_terminal_drained_sync_states() -> dict[str, int]:
    summary = crawl_task_service.summarize_video_task_states_by_sync_state()
    now = datetime.now()
    completed = 0
    failed = 0

    with get_session() as session:
        states = session.execute(
            select(SubscriptionSyncState).where(
                SubscriptionSyncState.sync_status == SyncStatus.RUNNING.value,
                SubscriptionSyncState.locked_at.is_(None),
            )
        ).scalars().all()

        for state in states:
            stats = summary.get(state.id, {})
            active_count = int(stats.get('active_count', 0) or 0)
            failed_count = int(stats.get('failed_count', 0) or 0)

            if active_count > 0:
                continue

            state.pending_video_count = 0

            if failed_count > 0:
                state.failure_count += 1
                state.sync_status = SyncStatus.FAILED.value
                state.last_sync_at = now
                state.last_error = str(stats.get('last_error') or 'video_extract_failed')
                state.queue_token = None
                state.queued_at = None
                state.locked_at = None
                state.idle_sync_count = 0
                state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
                state.version += 1
                _append_terminal_reconcile_run_events(
                    session,
                    state=state,
                    event_type=SyncEventType.FAILED,
                    event_phase=SyncPhase.FAILED,
                    event_status=SyncRunStatus.FAILED,
                    reason='video_extract_reconcile_failed',
                    error_message=state.last_error,
                    occurred_at=now,
                )
                failed += 1
                continue

            _complete_sync_success_in_session(session, state=state)
            _append_terminal_reconcile_run_events(
                session,
                state=state,
                event_type=SyncEventType.COMPLETED,
                event_phase=SyncPhase.COMPLETED,
                event_status=SyncRunStatus.SUCCESS,
                reason='video_extract_reconcile_completed',
                error_message=None,
                occurred_at=now,
            )
            completed += 1

    return {
        'running_states': len(states),
        'completed': completed,
        'failed': failed,
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


def _get_latest_state_run_projection(
    session: Session,
    state: SubscriptionSyncState,
) -> Optional[SubscriptionSyncRunProjection]:
    try:
        return session.execute(
            select(SubscriptionSyncRunProjection)
            .join(
                SubscriptionSyncSubscriptionProjection,
                SubscriptionSyncSubscriptionProjection.latest_run_id == SubscriptionSyncRunProjection.run_id,
            )
            .where(
                SubscriptionSyncSubscriptionProjection.subscription_id == state.subscription_id,
                SubscriptionSyncRunProjection.sync_state_id == state.id,
            )
            .limit(1)
        ).scalar_one_or_none()
    except SQLAlchemyError:
        return None


def _can_complete_drained_state(sync_state_id: int) -> bool:
    try:
        summary = crawl_task_service.summarize_video_task_states_by_sync_state()
    except SQLAlchemyError:
        return True

    stats = summary.get(sync_state_id, {})
    active_count = int(stats.get('active_count', 0) or 0)
    failed_count = int(stats.get('failed_count', 0) or 0)
    return failed_count == 0 and active_count <= 1


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
