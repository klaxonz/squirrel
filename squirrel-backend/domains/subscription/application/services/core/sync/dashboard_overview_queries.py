from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from domains.subscription.domain.models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from domains.subscription.application.services.core.sync.constants import DUE_SOON_WINDOW
from domains.subscription.application.services.core.sync.dashboard_projection_queries import (
    projection_filter_clauses,
    projection_pending_videos_expr,
    projection_phase_expr,
    projection_status_expr,
)
from domains.subscription.application.services.core.sync.progress import ACTIVE_EXTRACTION_PHASES


def load_overview_row(
    session: Session,
    *,
    user_id: int,
    site_candidates: set[str],
    normalized_query: str,
):
    current_status = projection_status_expr()
    current_phase = projection_phase_expr()
    pending_videos = projection_pending_videos_expr()
    now = datetime.now()

    return session.execute(
        select(
            func.coalesce(func.sum(case((
                and_(
                    current_status == 'running',
                    current_phase.notin_(ACTIVE_EXTRACTION_PHASES),
                ),
                1,
            ), else_=0)), 0).label('running_count'),
            func.coalesce(func.sum(case((
                and_(
                    current_status == 'running',
                    current_phase.in_(ACTIVE_EXTRACTION_PHASES),
                ),
                1,
            ), else_=0)), 0).label('awaiting_extract_count'),
            func.coalesce(func.sum(case(((current_status == 'queued'), 1), else_=0)), 0).label('queued_count'),
            func.coalesce(
                func.sum(case(((current_status.in_({'failed', 'timeout'})), 1), else_=0)),
                0,
            ).label('failed_count'),
            func.coalesce(func.sum(case((
                and_(
                    current_status.notin_({'running', 'queued', 'failed', 'timeout', 'deferred'}),
                    SubscriptionSyncSubscriptionProjection.next_sync_at.is_not(None),
                    SubscriptionSyncSubscriptionProjection.next_sync_at >= now,
                    SubscriptionSyncSubscriptionProjection.next_sync_at <= now + DUE_SOON_WINDOW,
                ),
                1,
            ), else_=0)), 0).label('due_soon_count'),
            func.coalesce(func.sum(case(((current_status == 'deferred'), 1), else_=0)), 0).label(
                'deferred_count',
            ),
            func.coalesce(func.sum(pending_videos), 0).label('pending_videos'),
        )
        .select_from(Subscription)
        .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
        .outerjoin(
            SubscriptionSyncSubscriptionProjection,
            SubscriptionSyncSubscriptionProjection.subscription_id == Subscription.id,
        )
        .outerjoin(
            SubscriptionSyncRunProjection,
            SubscriptionSyncRunProjection.run_id == SubscriptionSyncSubscriptionProjection.latest_run_id,
        )
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            Subscription.is_deleted.is_(False),
        )
        .where(*projection_filter_clauses(site_candidates=site_candidates, normalized_query=normalized_query)),
    ).one()
