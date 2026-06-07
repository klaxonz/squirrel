from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from . import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from utils.url_helper import resolve_site
from ._intervals import SYNC_BATCH_SIZE


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
            state.site = resolve_site(url)
        if state.next_sync_at is None:
            state.next_sync_at = datetime.now()
        return state

    state = SubscriptionSyncState(
        subscription_id=subscription_id,
        site=resolve_site(url),
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


def list_due_sync_states(
    mode: str,
    limit: int = SYNC_BATCH_SIZE,
    *,
    now: Optional[datetime] = None,
) -> list[tuple[SubscriptionSyncState, str]]:
    now = now or datetime.now()
    from ._recovery import _recover_stale_running_states_in_session
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


def increment_pending_video_count(sync_state_id: Optional[int], count: int = 1) -> None:
    if not sync_state_id or count <= 0:
        return
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return
        state.pending_video_count += count
        state.version += 1
