import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from core.database import get_session
from schemas.subscription.dto.sync_dashboard_dto import (
    SyncDashboardItemDto,
    SyncDashboardOverviewDto,
)
from services.observability.collector.instance import metrics
from services.site_catalog.cache import parse_datetime as _parse_datetime
from services.site_catalog.catalog import SiteCatalog
from services.subscription.sync.dashboard_feed_queries import load_feed_completed_at_map, load_recent_run_rows
from services.subscription.sync.dashboard_overview_queries import load_overview_row
from services.subscription.sync.dashboard_projection_queries import load_projection_rows
from services.subscription.sync.progress import subscription_sync_progress
from services.sync_dashboard.items import SyncDashboardItemFactory
from services.sync_dashboard.presentation import sort_items
from services.sync_dashboard.queue_ranks import sync_dashboard_queue_rank_service
from services.sync_dashboard.site_icons import SiteIconResolver

SYNC_DASHBOARD_PREVIEW_LIMIT = 40
SYNC_DASHBOARD_RECENT_SCAN_MULTIPLIER = 4
SYNC_DASHBOARD_RECENT_SCAN_MAX = 200

logger = logging.getLogger(__name__)


class SubscriptionSyncDashboardService:
    def __init__(
        self,
        session_factory=get_session,
        progress_service=None,
        item_factory=None,
        queue_rank_service=None,
    ):
        self.session_factory = session_factory
        self.progress_service = progress_service or subscription_sync_progress
        self.item_factory = item_factory or SyncDashboardItemFactory(
            progress_service=self.progress_service,
            site_icon_resolver=SiteIconResolver(),
        )
        self.queue_rank_service = queue_rank_service or sync_dashboard_queue_rank_service
        self._recent_run_snapshot_cache: dict[int, set[str]] = {}

    @staticmethod
    def _safe_metric_int(value: Any) -> int:
        if value in (None, ''):
            return 0
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _is_feed_running_item(item: SyncDashboardItemDto) -> bool:
        return item.display_status == 'running' and not item.feed_completed

    @staticmethod
    def _is_awaiting_extract_item(item: SyncDashboardItemDto) -> bool:
        return item.display_status == 'running' and item.feed_completed

    def _queue_metrics_overview(self) -> tuple[int, int]:
        queue_depth = sum(
            self._safe_metric_int(metrics.redis.get(key))
            for key in metrics.get_metrics_keys_by_pattern('metrics:gauge:queue.depth:*')
        )
        queue_messages = sum(
            self._safe_metric_int(metrics.redis.get(key))
            for key in metrics.get_metrics_keys_by_pattern('metrics:counter:queue.messages.total:*')
        )
        return queue_depth, queue_messages

    def _load_projection_items(
        self,
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
    ) -> list[SyncDashboardItemDto]:
        rows = load_projection_rows(
            session,
            user_id=user_id,
            filter_status=filter_status,
            order_status=order_status,
            site_candidates=site_candidates,
            normalized_query=normalized_query,
            page=page,
            page_size=page_size,
            limit=limit,
        )
        return [
            self.item_factory.build_item(subscription, subscription_projection, run_projection)
            for subscription, subscription_projection, run_projection in rows
        ]

    def _collect_projection_items(
        self,
        user_id: int,
        *,
        status: str | None = None,
        site_candidates: set[str] | None = None,
        normalized_query: str = '',
    ) -> list[SyncDashboardItemDto]:
        with self.session_factory() as session:
            return self._load_projection_items(
                session,
                user_id=user_id,
                filter_status=status,
                site_candidates=site_candidates,
                normalized_query=normalized_query,
            )

    def get_feed_dashboard_snapshot(
        self,
        user_id: int,
        site: str | None,
        query: str | None,
        date_from: str | None,
        date_to: str | None,
        recent_limit: int = SYNC_DASHBOARD_PREVIEW_LIMIT,
    ) -> dict:
        normalized_site = (site or '').strip().lower() or None
        site_candidates = set(SiteCatalog.expand_site_filter_values(normalized_site)) if normalized_site else set()
        normalized_query = (query or '').strip().lower()
        parsed_from = _parse_datetime(date_from)
        parsed_to = _parse_datetime(date_to)
        resolved_recent_limit = max(1, int(recent_limit or SYNC_DASHBOARD_PREVIEW_LIMIT))
        recent_scan_limit = min(
            max(resolved_recent_limit * SYNC_DASHBOARD_RECENT_SCAN_MULTIPLIER, resolved_recent_limit),
            SYNC_DASHBOARD_RECENT_SCAN_MAX,
        )

        queue_depth, queue_messages = self._queue_metrics_overview()
        with self.session_factory() as session:
            overview_row = load_overview_row(
                session,
                user_id=user_id,
                site_candidates=site_candidates,
                normalized_query=normalized_query,
            )

            running_preview = self._load_projection_items(
                session,
                user_id=user_id,
                filter_status='running',
                site_candidates=site_candidates,
                normalized_query=normalized_query,
                limit=int(overview_row.running_count or 0),
            )

            queued_preview = self._load_projection_items(
                session,
                user_id=user_id,
                filter_status='queued',
                site_candidates=site_candidates,
                normalized_query=normalized_query,
                limit=int(overview_row.queued_count or 0),
            )
            queued_candidate_rank_map, queued_backlog_rank_map = self.queue_rank_service.query_rank_maps(
                session,
                user_id,
                queued_preview,
            )
            queued_preview = sort_items(
                queued_preview,
                'queued',
                queued_candidate_rank_map=queued_candidate_rank_map,
                queued_backlog_rank_map=queued_backlog_rank_map,
            )
            for index, item in enumerate(queued_preview, start=1):
                item.queue_position = index

            recent_rows = load_recent_run_rows(
                session,
                user_id=user_id,
                site_candidates=site_candidates,
                normalized_query=normalized_query,
                parsed_from=parsed_from,
                parsed_to=parsed_to,
                limit=recent_scan_limit,
            )
            feed_completed_at_map = load_feed_completed_at_map(
                session,
                [run_projection.run_id for run_projection, _ in recent_rows if run_projection and run_projection.run_id],
            )

        recent_rows = sorted(
            recent_rows,
            key=lambda row: (
                feed_completed_at_map.get(row[0].run_id)
                or row[0].finished_at
                or row[0].last_event_at
                or row[0].started_at
                or datetime.min,
                row[0].run_id,
            ),
            reverse=True,
        )
        recent_runs = [
            self.item_factory.serialize_recent_run(run_projection, subscription, feed_completed_at_map.get(run_projection.run_id))
            for run_projection, subscription in recent_rows
        ][:resolved_recent_limit]

        # 计算新增的已完成运行（上一轮未返回过的）
        previous_run_ids = self._recent_run_snapshot_cache.get(user_id, set())
        current_run_ids = {run['run_id'] for run in recent_runs}
        newly_completed = [
            run for run in recent_runs
            if run['run_id'] not in previous_run_ids
        ][:5]

        # 更新缓存为当前轮次的 run_id 集合
        self._recent_run_snapshot_cache[user_id] = current_run_ids

        overview = SyncDashboardOverviewDto(
            running_count=int(overview_row.running_count or 0),
            awaiting_extract_count=int(overview_row.awaiting_extract_count or 0),
            queued_count=int(overview_row.queued_count or 0),
            failed_count=int(overview_row.failed_count or 0),
            due_soon_count=int(overview_row.due_soon_count or 0),
            deferred_count=int(overview_row.deferred_count or 0),
            pending_videos=int(overview_row.pending_videos or 0),
            queue_depth=queue_depth,
            queue_messages=queue_messages,
        )

        return {
            'overview': overview,
            'runningPreview': running_preview,
            'queuedPreview': queued_preview,
            'recentRuns': recent_runs,
            'recentlyCompletedRuns': newly_completed,
        }


subscription_sync_dashboard_service = SubscriptionSyncDashboardService()
