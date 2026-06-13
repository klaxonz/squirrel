from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from models.subscription_sync_trend_projection import SubscriptionSyncTrendProjection
from services.subscription.sync.run_service import SyncRunStatus


def advisory_lock(session: Session, key: str) -> None:
    session.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'), {'key': key})


def get_or_create_run_projection(session: Session, event: SubscriptionSyncEvent) -> SubscriptionSyncRunProjection:
    advisory_lock(session, f'run-sync-projection:{event.stream_id}')
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


def get_or_create_subscription_projection(
    session: Session,
    event: SubscriptionSyncEvent,
) -> SubscriptionSyncSubscriptionProjection:
    advisory_lock(session, f'subscription-sync-projection:{event.subscription_id}')
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


def get_or_create_trend_projection(
    session: Session,
    *,
    bucket_time: datetime,
    bucket_granularity: str,
    site: str,
    sync_mode: str,
    trigger: str,
) -> SubscriptionSyncTrendProjection:
    advisory_lock(
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
