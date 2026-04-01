from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.orm import Session

from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_task import CrawlTask
from services.crawl_dispatcher.policy import CrawlDispatcherPolicy
from services.crawl_tasks.models import CrawlTaskStatus
from services.crawl_tasks import service as crawl_task_service


class CrawlDispatcherService:
    def __init__(self, *, policy: Optional[CrawlDispatcherPolicy] = None):
        self.policy = policy or CrawlDispatcherPolicy.from_settings()

    def claim_next(self, *, worker_id: str, now: Optional[datetime] = None, lease_seconds: int = 60):
        now = now or datetime.now()
        with crawl_task_service.get_session() as session:
            candidate_ids = session.execute(self._build_candidate_query(now)).scalars().all()
            for candidate_id in candidate_ids:
                task = self._try_claim_candidate(
                    session,
                    task_id=int(candidate_id),
                    worker_id=worker_id,
                    now=now,
                    lease_seconds=lease_seconds,
                )
                if task is not None:
                    return task
        return None

    def _build_candidate_query(self, now: datetime):
        priority_order = case(
            (CrawlTask.priority == 'manual', 3),
            (CrawlTask.priority == 'normal', 2),
            (CrawlTask.priority == 'low', 1),
            else_=0,
        )
        runnable_tasks = (
            select(
                CrawlTask.id.label('task_id'),
                priority_order.label('priority_rank'),
                CrawlTask.next_run_at.label('next_run_at'),
                CrawlTask.created_at.label('created_at'),
                func.row_number().over(
                    partition_by=CrawlTask.site,
                    order_by=(
                        priority_order.desc(),
                        CrawlTask.next_run_at.asc(),
                        CrawlTask.created_at.asc(),
                        CrawlTask.id.asc(),
                    ),
                ).label('site_rank'),
                func.row_number().over(
                    partition_by=CrawlTask.task_type,
                    order_by=(
                        priority_order.desc(),
                        CrawlTask.next_run_at.asc(),
                        CrawlTask.created_at.asc(),
                        CrawlTask.id.asc(),
                    ),
                ).label('task_type_rank'),
            )
            .where(
                CrawlTask.status.in_([CrawlTaskStatus.PENDING.value, CrawlTaskStatus.RETRY_WAIT.value]),
                CrawlTask.next_run_at <= now,
                or_(CrawlTask.lease_until.is_(None), CrawlTask.lease_until < now),
            )
            .subquery()
        )
        site_heads = select(
            runnable_tasks.c.task_id,
            literal(1).label('source_rank'),
            runnable_tasks.c.priority_rank,
            runnable_tasks.c.next_run_at,
            runnable_tasks.c.created_at,
        ).where(runnable_tasks.c.site_rank == 1)
        task_type_heads = select(
            runnable_tasks.c.task_id,
            literal(0).label('source_rank'),
            runnable_tasks.c.priority_rank,
            runnable_tasks.c.next_run_at,
            runnable_tasks.c.created_at,
        ).where(runnable_tasks.c.task_type_rank == 1)
        candidate_pool = site_heads.union_all(task_type_heads).subquery()
        candidate_rows = (
            select(
                candidate_pool.c.task_id.label('task_id'),
                func.min(candidate_pool.c.source_rank).label('source_rank'),
                func.max(candidate_pool.c.priority_rank).label('priority_rank'),
                func.min(candidate_pool.c.next_run_at).label('next_run_at'),
                func.min(candidate_pool.c.created_at).label('created_at'),
            )
            .group_by(candidate_pool.c.task_id)
            .subquery()
        )
        return (
            select(candidate_rows.c.task_id)
            .where(
                candidate_rows.c.task_id.is_not(None),
            )
            .order_by(
                candidate_rows.c.source_rank.asc(),
                candidate_rows.c.priority_rank.desc(),
                candidate_rows.c.next_run_at.asc(),
                candidate_rows.c.created_at.asc(),
                candidate_rows.c.task_id.asc(),
            )
            .limit(100)
        )

    def _try_claim_candidate(
        self,
        session: Session,
        *,
        task_id: int,
        worker_id: str,
        now: datetime,
        lease_seconds: int,
    ):
        task = session.execute(
            select(CrawlTask)
            .where(
                CrawlTask.id == task_id,
                CrawlTask.status.in_([CrawlTaskStatus.PENDING.value, CrawlTaskStatus.RETRY_WAIT.value]),
                CrawlTask.next_run_at <= now,
                or_(CrawlTask.lease_until.is_(None), CrawlTask.lease_until < now),
            )
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        if task is None:
            return None

        self._lock_scope(session, scope_type='site', scope_key=task.site)
        self._lock_scope(session, scope_type='task_type', scope_key=task.task_type)

        site_running = self._count_running_tasks(session, site=task.site)
        if not self.policy.is_site_available(task.site, site_running):
            return None

        task_type_running = self._count_running_tasks(session, task_type=task.task_type)
        if not self.policy.is_task_type_available(task.task_type, task_type_running):
            return None

        task.status = CrawlTaskStatus.LEASED.value
        task.worker_id = worker_id
        task.lease_until = now + timedelta(seconds=lease_seconds)
        session.flush()
        return task

    def _lock_scope(self, session: Session, *, scope_type: str, scope_key: str) -> CrawlDispatchScope:
        crawl_task_service._ensure_dispatch_scope(session, scope_type=scope_type, scope_key=scope_key)
        scope = session.execute(
            select(CrawlDispatchScope)
            .where(
                CrawlDispatchScope.scope_type == scope_type,
                CrawlDispatchScope.scope_key == scope_key,
            )
            .with_for_update()
        ).scalar_one()
        return scope

    @staticmethod
    def _count_running_tasks(session: Session, *, site: Optional[str] = None, task_type: Optional[str] = None) -> int:
        query = select(func.count(CrawlTask.id)).where(
            CrawlTask.status.in_([CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value])
        )
        if site is not None:
            query = query.where(CrawlTask.site == site)
        if task_type is not None:
            query = query.where(CrawlTask.task_type == task_type)
        value = session.execute(query).scalar_one()
        return int(value or 0)
