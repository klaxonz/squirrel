from datetime import datetime
from typing import Any

from domains.subscription.application.services.core.sync.dashboard_feed_queries import load_feed_completed_at_map
from domains.subscription.application.services.core.sync.history_queries import (
    build_run_list_query,
    count_query_rows,
    load_run_detail_row,
    load_run_events,
    payload_metric_value,
    run_exists_for_user,
)
from domains.subscription.application.services.core.sync.history_serialization import (
    parse_datetime,
    serialize_event,
    serialize_run,
)
from domains.subscription.application.services.core.sync.progress import subscription_sync_progress
from domains.subscription.application.services.sync.site_icons import SiteIconResolver
from domains.subscription.domain.models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from infrastructure.database.session import get_session


class SubscriptionSyncHistoryService:
    def __init__(self, session_factory=get_session, progress_service=None, site_icon_resolver=None):
        self.session_factory = session_factory
        self.progress_service = progress_service or subscription_sync_progress
        self.site_icon_resolver = site_icon_resolver or SiteIconResolver()

    def list_runs(
        self,
        user_id: int,
        *,
        status: str | None = None,
        site: str | None = None,
        subscription_id: int | None = None,
        mode: str | None = None,
        trigger: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        query, normalized_status = build_run_list_query(
            user_id,
            status=status,
            site=site,
            subscription_id=subscription_id,
            mode=mode,
            trigger=trigger,
            parsed_from=parse_datetime(date_from),
            parsed_to=parse_datetime(date_to),
        )

        with self.session_factory() as session:
            if normalized_status == 'feed_recent':
                all_rows = session.execute(query).all()
                feed_completed_at_map = load_feed_completed_at_map(
                    session,
                    [run.run_id for run, _ in all_rows if run and run.run_id],
                )
                sorted_rows = sorted(
                    all_rows,
                    key=lambda row: self._feed_recent_sort_key(row, feed_completed_at_map),
                    reverse=True,
                )
                rows = sorted_rows[(page - 1) * page_size: page * page_size]
                total = len(all_rows)
            else:
                rows = session.execute(
                    query.order_by(SubscriptionSyncRunProjection.last_event_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                ).all()
                total = count_query_rows(session, query)
                feed_completed_at_map = {}

        return {
            'total': total,
            'page': page,
            'pageSize': page_size,
            'data': [
                serialize_run(
                    run,
                    subscription,
                    progress_service=self.progress_service,
                    site_icon_resolver=self.site_icon_resolver,
                    feed_completed_at=feed_completed_at_map.get(run.run_id),
                    include_feed_completed_at=True,
                )
                for run, subscription in rows
            ],
        }

    @staticmethod
    def _feed_recent_sort_key(row: Any, feed_completed_at_map: dict[str, datetime]) -> tuple:
        run, _ = row
        return (
            feed_completed_at_map.get(run.run_id)
            or run.finished_at
            or run.last_event_at
            or run.started_at
            or datetime.min,
            run.run_id,
        )

    def get_run_detail(self, run_id: str, user_id: int) -> dict | None:
        with self.session_factory() as session:
            row = load_run_detail_row(session, run_id, user_id)
            if not row:
                return None
            run, subscription = row
            source_video_count = payload_metric_value(session, run.run_id, 'source_video_count')

        return serialize_run(
            run,
            subscription,
            progress_service=self.progress_service,
            site_icon_resolver=self.site_icon_resolver,
            source_video_count=source_video_count,
            include_detail_fields=True,
        )

    def get_run_detail_snapshot(self, run_id: str, user_id: int) -> dict | None:
        run = self.get_run_detail(run_id, user_id)
        if not run:
            return None
        return {
            'run': run,
            'events': self.list_run_events(run_id, user_id),
        }

    def list_run_events(self, run_id: str, user_id: int) -> list[dict]:
        with self.session_factory() as session:
            if not run_exists_for_user(session, run_id, user_id):
                return []
            events = load_run_events(session, run_id)
        return [serialize_event(event) for event in events]


subscription_sync_history_service = SubscriptionSyncHistoryService()
