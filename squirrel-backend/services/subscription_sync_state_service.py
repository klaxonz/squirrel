from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import exists, select, update

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from utils import url_helper


INCREMENTAL_INTERVAL = timedelta(minutes=5)
FULL_INTERVAL = timedelta(hours=2)
INCREMENTAL_PENDING_THRESHOLD = 15
RUNNING_TIMEOUT = timedelta(minutes=30)


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


def list_due_sync_states(mode: str, limit: int = 200) -> list[tuple[SubscriptionSyncState, str]]:
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
        state.sync_status = SyncStatus.FAILED.value
        state.last_error = 'stale_running_timeout'
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.failure_count += 1
        state.next_sync_at = now
        state.version += 1


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
        state.sync_status = SyncStatus.FAILED.value
        state.last_error = 'stale_running_timeout'
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.failure_count += 1
        state.next_sync_at = now
        state.version += 1
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


def claim_sync_state(sync_state_id: int, queue_token: str) -> Optional[SubscriptionSyncState]:
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
        return session.execute(
            select(SubscriptionSyncState).where(SubscriptionSyncState.id == sync_state_id)
        ).scalar_one_or_none()


def mark_sync_success(
    sync_state_id: int,
    *,
    cursor_payload: Optional[dict],
    latest_video_url: Optional[str],
    next_sync_at: Optional[datetime] = None,
) -> Optional[SubscriptionSyncState]:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        state.sync_status = SyncStatus.SUCCESS.value
        state.cursor_payload = cursor_payload or {}
        if latest_video_url:
            state.last_seen_video_url = latest_video_url
        state.last_sync_at = now
        state.last_success_at = now
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.failure_count = 0
        state.last_error = None
        state.next_sync_at = next_sync_at or (now + get_mode_interval(state.sync_mode))
        state.version += 1
        return state


def mark_sync_skipped(sync_state_id: int, *, next_sync_at: Optional[datetime] = None) -> Optional[SubscriptionSyncState]:
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
        return state


def mark_sync_failed(sync_state_id: int, error_message: str) -> Optional[SubscriptionSyncState]:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        state.failure_count += 1
        state.sync_status = SyncStatus.FAILED.value
        state.last_sync_at = now
        state.last_error = error_message
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
        state.version += 1
        return state


def defer_sync_state(sync_state_id: int, *, delay: timedelta, error_message: Optional[str] = None) -> Optional[SubscriptionSyncState]:
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
        state.next_sync_at = now + delay
        state.version += 1
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


def decrement_pending_video_count(sync_state_id: Optional[int], count: int = 1) -> None:
    if not sync_state_id or count <= 0:
        return
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return
        state.pending_video_count = max(0, state.pending_video_count - count)
        state.version += 1


def build_queue_token() -> str:
    return uuid4().hex


def has_incremental_backpressure(sync_state: SubscriptionSyncState) -> bool:
    return sync_state.sync_mode == SyncMode.INCREMENTAL.value and sync_state.pending_video_count >= INCREMENTAL_PENDING_THRESHOLD


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
