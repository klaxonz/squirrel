from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from services.subscription_sync_progress import ACTIVE_EXTRACTION_PHASES
from services.subscription_sync_run_service import SyncEventType

DUE_SOON_WINDOW = timedelta(minutes=30)
FEED_RECENT_PHASES = {'extracting', 'finalizing', 'completed'}
FEED_HANDOFF_EVENT_TYPES = {'phase_changed', 'continued'}
FEED_HANDOFF_PHASES = {'extracting', 'finalizing'}


class SyncCenterQueriesService:
    def __init__(self, session_factory=get_session):
        self.session_factory = session_factory

    @staticmethod
    def _base_projection_query(user_id: int) -> Any:
        return (
            select(Subscription, SubscriptionSyncSubscriptionProjection, SubscriptionSyncRunProjection)
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
        )

    @staticmethod
    def _projection_status_expr() -> Any:
        return func.coalesce(SubscriptionSyncSubscriptionProjection.current_status, '')

    @staticmethod
    def _projection_phase_expr() -> Any:
        return func.coalesce(
            SubscriptionSyncRunProjection.current_phase,
            SubscriptionSyncSubscriptionProjection.current_phase,
            '',
        )

    @staticmethod
    def _projection_pending_videos_expr() -> Any:
        return func.coalesce(
            SubscriptionSyncSubscriptionProjection.pending_video_count,
            SubscriptionSyncRunProjection.pending_video_count,
            0,
        )

    @staticmethod
    def _apply_projection_filters(query: Any, *, status: str | None = None, site_candidates: set[str] | None = None, normalized_query: str = '') -> Any:
        clauses = SyncCenterQueriesService._projection_filter_clauses(
            status=status,
            site_candidates=site_candidates,
            normalized_query=normalized_query,
        )
        if clauses:
            query = query.where(*clauses)
        return query

    @staticmethod
    def _projection_filter_clauses(*, status: str | None = None, site_candidates: set[str] | None = None, normalized_query: str = '') -> list[Any]:
        clauses = []
        normalized_status = (status or '').strip().lower() or None
        current_status = SyncCenterQueriesService._projection_status_expr()
        current_phase = SyncCenterQueriesService._projection_phase_expr()
        if normalized_status == 'running':
            clauses.extend([
                current_status == 'running',
                current_phase.notin_(ACTIVE_EXTRACTION_PHASES),
            ])
        elif normalized_status == 'queued':
            clauses.append(current_status == 'queued')
        elif normalized_status == 'failed':
            clauses.append(current_status.in_({'failed', 'timeout'}))
        elif normalized_status == 'deferred':
            clauses.append(current_status == 'deferred')
        elif normalized_status == 'scheduled':
            now = datetime.now()
            clauses.extend([
                current_status.notin_({'running', 'queued', 'failed', 'timeout', 'deferred'}),
                SubscriptionSyncSubscriptionProjection.next_sync_at.is_not(None),
                SubscriptionSyncSubscriptionProjection.next_sync_at >= now,
                SubscriptionSyncSubscriptionProjection.next_sync_at <= now + DUE_SOON_WINDOW,
            ])

        if site_candidates:
            clauses.append(SubscriptionSyncRunProjection.site.in_(site_candidates))
        if normalized_query:
            clauses.append(Subscription.name.ilike(f'%{normalized_query}%'))

        return clauses

    @staticmethod
    def _apply_projection_ordering(query: Any, status: str | None) -> Any:
        normalized_status = (status or '').strip().lower() or None
        if normalized_status == 'running':
            return query.order_by(
                SubscriptionSyncRunProjection.started_at.asc(),
                Subscription.id.asc(),
            )
        if normalized_status == 'queued':
            return query.order_by(
                SubscriptionSyncRunProjection.queued_at.asc(),
                Subscription.id.asc(),
            )
        if normalized_status == 'scheduled':
            return query.order_by(
                SubscriptionSyncSubscriptionProjection.next_sync_at.asc(),
                Subscription.id.asc(),
            )
        if normalized_status == 'recent':
            return query.order_by(
                func.coalesce(
                    SubscriptionSyncSubscriptionProjection.updated_at,
                    SubscriptionSyncRunProjection.updated_at,
                    SubscriptionSyncRunProjection.started_at,
                    SubscriptionSyncRunProjection.queued_at,
                    SubscriptionSyncSubscriptionProjection.last_sync_at,
                    SubscriptionSyncSubscriptionProjection.last_success_at,
                ).desc(),
                Subscription.id.desc(),
            )
        return query.order_by(
            func.coalesce(
                SubscriptionSyncSubscriptionProjection.last_sync_at,
                SubscriptionSyncSubscriptionProjection.updated_at,
                SubscriptionSyncRunProjection.updated_at,
            ).desc(),
            Subscription.id.desc(),
        )

    @staticmethod
    def _load_projection_rows(
        session: Session,
        *,
        user_id: int,
        filter_status: str | None = None,
        order_status: str | None = None,
        site_candidates: set[str] | None = None,
        normalized_query: str = '',
        page: int | None = None,
        page_size: int | None = None,
        limit: int | None = None,
    ):
        filtered_query = SyncCenterQueriesService._apply_projection_filters(
            SyncCenterQueriesService._base_projection_query(user_id),
            status=filter_status,
            site_candidates=site_candidates,
            normalized_query=normalized_query,
        )
        ordered_query = SyncCenterQueriesService._apply_projection_ordering(filtered_query, order_status if order_status is not None else filter_status)

        if page is not None and page_size is not None:
            start = max(0, (page - 1) * page_size)
            ordered_query = ordered_query.offset(start).limit(page_size)
        elif limit is not None:
            ordered_query = ordered_query.limit(limit)

        return session.execute(ordered_query).all()

    @staticmethod
    def _load_feed_completed_at_map(session: Session, run_ids: list[str]) -> dict[str, datetime]:
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


_default = SyncCenterQueriesService()
_base_projection_query = _default._base_projection_query
_projection_status_expr = _default._projection_status_expr
_projection_phase_expr = _default._projection_phase_expr
_projection_pending_videos_expr = _default._projection_pending_videos_expr
_apply_projection_filters = _default._apply_projection_filters
_projection_filter_clauses = _default._projection_filter_clauses
_apply_projection_ordering = _default._apply_projection_ordering
_load_projection_rows = _default._load_projection_rows
_load_feed_completed_at_map = _default._load_feed_completed_at_map
