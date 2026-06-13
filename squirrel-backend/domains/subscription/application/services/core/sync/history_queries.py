from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from infrastructure.site_catalog.catalog import SiteCatalog
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_event import SubscriptionSyncEvent
from domains.subscription.domain.models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from domains.subscription.domain.models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from domains.subscription.application.services.core.sync.constants import FEED_RECENT_PHASES, TERMINAL_RUN_STATUSES


def base_run_query(user_id: int) -> Any:
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


def build_run_list_query(
    user_id: int,
    *,
    status: str | None = None,
    site: str | None = None,
    subscription_id: int | None = None,
    mode: str | None = None,
    trigger: str | None = None,
    parsed_from: datetime | None = None,
    parsed_to: datetime | None = None,
) -> tuple[Any, str | None]:
    query = base_run_query(user_id)
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
    if parsed_from:
        filters.append(SubscriptionSyncRunProjection.last_event_at >= parsed_from)
    if parsed_to:
        filters.append(SubscriptionSyncRunProjection.last_event_at <= parsed_to)

    if filters:
        query = query.where(and_(*filters))

    if normalized_status == 'feed_recent':
        query = query.join(
            SubscriptionSyncSubscriptionProjection,
            SubscriptionSyncSubscriptionProjection.subscription_id == SubscriptionSyncRunProjection.subscription_id,
        ).where(
            SubscriptionSyncSubscriptionProjection.latest_run_id == SubscriptionSyncRunProjection.run_id
        )

    return query, normalized_status


def count_query_rows(session: Session, query: Any) -> int:
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    return int(session.execute(count_query).scalar() or 0)


def load_run_detail_row(session: Session, run_id: str, user_id: int):
    return session.execute(
        base_run_query(user_id).where(SubscriptionSyncRunProjection.run_id == run_id)
    ).first()


def run_exists_for_user(session: Session, run_id: str, user_id: int) -> bool:
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


def load_run_events(session: Session, run_id: str) -> list[SubscriptionSyncEvent]:
    return session.execute(
        select(SubscriptionSyncEvent)
        .where(SubscriptionSyncEvent.stream_id == run_id)
        .order_by(SubscriptionSyncEvent.seq_no.asc(), SubscriptionSyncEvent.occurred_at.asc())
    ).scalars().all()


def payload_metric_value(session: Session, run_id: str, key: str) -> int | None:
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
