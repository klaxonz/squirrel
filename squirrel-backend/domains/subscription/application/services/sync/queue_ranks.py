from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.interfaces.dto.dto.sync_dashboard_dto import SyncDashboardItemDto
from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.application.services.crawl.tasks.task_types import subscription_sync_task_types


class SyncDashboardQueueRankService:
    @staticmethod
    def query_rank_maps(
        session: Session,
        user_id: int,
        items: list[SyncDashboardItemDto],
    ) -> tuple[dict[int, int], dict[int, int]]:
        subscription_ids = sorted({item.subscription_id for item in items})
        if not subscription_ids:
            return {}, {}

        priority_order = case(
            (CrawlTask.priority == 'manual', 3),
            (CrawlTask.priority == 'normal', 2),
            (CrawlTask.priority == 'low', 1),
            else_=0,
        )

        queued_task_rows = session.execute(
            select(CrawlTask.id, CrawlTask.subscription_id)
            .join(UserSubscription, UserSubscription.subscription_id == CrawlTask.subscription_id)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                CrawlTask.task_type.in_(subscription_sync_task_types()),
                CrawlTask.subscription_id.in_(subscription_ids),
                CrawlTask.status.in_([CrawlTaskStatus.PENDING.value, CrawlTaskStatus.RETRY_WAIT.value]),
            )
            .order_by(
                priority_order.desc(),
                CrawlTask.next_run_at.asc(),
                CrawlTask.created_at.asc(),
                CrawlTask.id.asc(),
            ),
        ).all()

        from domains.subscription.application.services.crawl.dispatcher.service import CrawlDispatcherService

        candidate_task_ids = session.execute(
            CrawlDispatcherService().build_candidate_query(datetime.now()),
        ).scalars().all()

        queued_task_map = {int(task_id): int(subscription_id) for task_id, subscription_id in queued_task_rows}
        candidate_subscription_ids: list[int] = []
        for task_id in candidate_task_ids:
            subscription_id = queued_task_map.get(int(task_id))
            if subscription_id is None or subscription_id in candidate_subscription_ids:
                continue
            candidate_subscription_ids.append(subscription_id)

        queued_subscription_ids = [int(subscription_id) for _, subscription_id in queued_task_rows]

        candidate_rank_map: dict[int, int] = {}
        for subscription_id in candidate_subscription_ids:
            if subscription_id in candidate_rank_map:
                continue
            candidate_rank_map[subscription_id] = len(candidate_rank_map) + 1

        backlog_rank_map: dict[int, int] = {}
        for subscription_id in queued_subscription_ids:
            if subscription_id in backlog_rank_map:
                continue
            backlog_rank_map[subscription_id] = len(backlog_rank_map) + 1

        return candidate_rank_map, backlog_rank_map


sync_dashboard_queue_rank_service = SyncDashboardQueueRankService()
