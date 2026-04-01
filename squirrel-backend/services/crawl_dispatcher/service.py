from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select

from models.crawl_task import CrawlTask
from services.crawl_dispatcher.models import DispatcherQuotaSnapshot
from services.crawl_dispatcher.policy import CrawlDispatcherPolicy
from services.crawl_tasks.models import CrawlTaskStatus
from services.crawl_tasks import service as crawl_task_service


class CrawlDispatcherService:
    def __init__(self, *, policy: Optional[CrawlDispatcherPolicy] = None):
        self.policy = policy or CrawlDispatcherPolicy.from_settings()

    def claim_next(self, *, worker_id: str, now: Optional[datetime] = None, lease_seconds: int = 60):
        now = now or datetime.now()
        snapshot = self._build_quota_snapshot()
        runnable_sites = self._list_runnable_sites(now)
        runnable_task_types = self._list_runnable_task_types(now)

        allowed_sites = [
            site for site in runnable_sites
            if self.policy.is_site_available(site, snapshot.site_running.get(site, 0))
        ]
        allowed_task_types = [
            task_type for task_type in runnable_task_types
            if self.policy.is_task_type_available(task_type, snapshot.task_type_running.get(task_type, 0))
        ]

        if not allowed_sites or not allowed_task_types:
            return None

        return crawl_task_service.claim_next_task(
            worker_id=worker_id,
            now=now,
            lease_seconds=lease_seconds,
            allowed_sites=allowed_sites,
            allowed_task_types=allowed_task_types,
        )

    def _build_quota_snapshot(self) -> DispatcherQuotaSnapshot:
        with crawl_task_service.get_session() as session:
            site_rows = session.execute(
                select(CrawlTask.site, func.count(CrawlTask.id))
                .where(CrawlTask.status.in_([CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value]))
                .group_by(CrawlTask.site)
            ).all()
            task_type_rows = session.execute(
                select(CrawlTask.task_type, func.count(CrawlTask.id))
                .where(CrawlTask.status.in_([CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value]))
                .group_by(CrawlTask.task_type)
            ).all()

        return DispatcherQuotaSnapshot(
            site_running={row[0]: int(row[1]) for row in site_rows},
            task_type_running={row[0]: int(row[1]) for row in task_type_rows},
        )

    def _list_runnable_sites(self, now: datetime) -> list[str]:
        with crawl_task_service.get_session() as session:
            rows = session.execute(
                select(CrawlTask.site)
                .where(
                    CrawlTask.status.in_([CrawlTaskStatus.PENDING.value, CrawlTaskStatus.RETRY_WAIT.value]),
                    CrawlTask.next_run_at <= now,
                    or_(CrawlTask.lease_until.is_(None), CrawlTask.lease_until < now),
                )
                .distinct()
            ).all()
        return [str(row[0]) for row in rows if row[0]]

    def _list_runnable_task_types(self, now: datetime) -> list[str]:
        with crawl_task_service.get_session() as session:
            rows = session.execute(
                select(CrawlTask.task_type)
                .where(
                    CrawlTask.status.in_([CrawlTaskStatus.PENDING.value, CrawlTaskStatus.RETRY_WAIT.value]),
                    CrawlTask.next_run_at <= now,
                    or_(CrawlTask.lease_until.is_(None), CrawlTask.lease_until < now),
                )
                .distinct()
            ).all()
        return [str(row[0]) for row in rows if row[0]]
