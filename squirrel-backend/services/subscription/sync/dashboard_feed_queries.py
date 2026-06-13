from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from services.search.query import escape_ilike
from services.subscription.sync.constants import FEED_RECENT_PHASES, TERMINAL_RUN_STATUSES
from services.subscription.sync.run_service import SyncEventType

FEED_HANDOFF_EVENT_TYPES = {'phase_changed', 'continued'}
FEED_HANDOFF_PHASES = {'extracting', 'finalizing'}


def load_recent_run_rows(
    session: Session,
    *,
    user_id: int,
    site_candidates: set[str],
    normalized_query: str,
    parsed_from: datetime | None,
    parsed_to: datetime | None,
    limit: int,
):
    recent_query = (
        select(SubscriptionSyncRunProjection, Subscription)
        .join(Subscription, Subscription.id == SubscriptionSyncRunProjection.subscription_id)
        .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
        .join(
            SubscriptionSyncSubscriptionProjection,
            SubscriptionSyncSubscriptionProjection.subscription_id == SubscriptionSyncRunProjection.subscription_id,
        )
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            Subscription.is_deleted.is_(False),
            SubscriptionSyncSubscriptionProjection.latest_run_id == SubscriptionSyncRunProjection.run_id,
            or_(
                SubscriptionSyncRunProjection.status.in_(TERMINAL_RUN_STATUSES),
                and_(
                    SubscriptionSyncRunProjection.status == 'running',
                    SubscriptionSyncRunProjection.current_phase.in_(FEED_RECENT_PHASES),
                ),
            ),
        )
    )
    if site_candidates:
        recent_query = recent_query.where(SubscriptionSyncRunProjection.site.in_(site_candidates))
    if normalized_query:
        recent_query = recent_query.where(Subscription.name.ilike(f'%{escape_ilike(normalized_query)}%'))
    if parsed_from:
        recent_query = recent_query.where(SubscriptionSyncRunProjection.last_event_at >= parsed_from)
    if parsed_to:
        recent_query = recent_query.where(SubscriptionSyncRunProjection.last_event_at <= parsed_to)

    return session.execute(
        recent_query.order_by(SubscriptionSyncRunProjection.last_event_at.desc()).limit(limit),
    ).all()


def load_feed_completed_at_map(session: Session, run_ids: list[str]) -> dict[str, datetime]:
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
        .group_by(SubscriptionSyncEvent.stream_id),
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
        .group_by(SubscriptionSyncEvent.stream_id),
    ).all()

    for stream_id, occurred_at in completed_rows:
        if stream_id and occurred_at:
            feed_completed_at_map[str(stream_id)] = occurred_at

    return feed_completed_at_map
