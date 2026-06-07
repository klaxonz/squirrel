from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.orm import Session

from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_task import CrawlTask
from services.crawl_dispatcher.policy import CrawlDispatcherPolicy
from services.crawl_tasks.models import CrawlTaskStatus
from services.crawl_tasks.service import CrawlTaskService


class CrawlDispatcherService:
    def __init__(
        self,
        *,
        policy: CrawlDispatcherPolicy | None = None,
        session_factory=None,
    ) -> None:
        self.policy = policy or CrawlDispatcherPolicy.from_settings()
        self.session_factory = session_factory

    def claim_next(self, *, worker_id: str, now: datetime | None = None, lease_seconds: int = 60) -> CrawlTask | None:
        now = now or datetime.now()
        with self._get_session() as session:
            candidate_rows = session.execute(self._build_candidate_query(now)).mappings().all()
            candidate_rows = self._sort_candidates_by_runtime_pressure(session, candidate_rows)
            for candidate_row in candidate_rows:
                claim_attempt = session.begin_nested()
                try:
                    task = self._try_claim_candidate(
                        session,
                        task_id=int(candidate_row["task_id"]),
                        worker_id=worker_id,
                        now=now,
                        lease_seconds=lease_seconds,
                    )
                except (ValueError, TypeError, AttributeError):
                    claim_attempt.rollback()
                    raise
                if task is not None:
                    claim_attempt.commit()
                    return task
                claim_attempt.rollback()
        return None

    def _build_candidate_query(self, now: datetime) -> Any:
        priority_order = case(
            (CrawlTask.priority == "manual", 3),
            (CrawlTask.priority == "normal", 2),
            (CrawlTask.priority == "low", 1),
            else_=0,
        )
        runnable_tasks = (
            select(
                CrawlTask.id.label("task_id"),
                CrawlTask.site.label("site"),
                CrawlTask.task_type.label("task_type"),
                priority_order.label("priority_rank"),
                CrawlTask.next_run_at.label("next_run_at"),
                CrawlTask.created_at.label("created_at"),
                func.row_number().over(
                    partition_by=(CrawlTask.site, CrawlTask.task_type),
                    order_by=(
                        priority_order.desc(),
                        CrawlTask.next_run_at.asc(),
                        CrawlTask.created_at.asc(),
                        CrawlTask.id.asc(),
                    ),
                ).label("site_rank"),
                func.row_number().over(
                    partition_by=CrawlTask.task_type,
                    order_by=(
                        priority_order.desc(),
                        CrawlTask.next_run_at.asc(),
                        CrawlTask.created_at.asc(),
                        CrawlTask.id.asc(),
                    ),
                ).label("task_type_rank"),
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
            runnable_tasks.c.site,
            runnable_tasks.c.task_type,
            literal(1).label("source_rank"),
            runnable_tasks.c.priority_rank,
            runnable_tasks.c.next_run_at,
            runnable_tasks.c.created_at,
        ).where(runnable_tasks.c.site_rank == 1)
        task_type_heads = select(
            runnable_tasks.c.task_id,
            runnable_tasks.c.site,
            runnable_tasks.c.task_type,
            literal(0).label("source_rank"),
            runnable_tasks.c.priority_rank,
            runnable_tasks.c.next_run_at,
            runnable_tasks.c.created_at,
        ).where(runnable_tasks.c.task_type_rank == 1)
        candidate_pool = site_heads.union_all(task_type_heads).subquery()
        candidate_rows = (
            select(
                candidate_pool.c.task_id.label("task_id"),
                candidate_pool.c.site.label("site"),
                candidate_pool.c.task_type.label("task_type"),
                func.min(candidate_pool.c.source_rank).label("source_rank"),
                func.max(candidate_pool.c.priority_rank).label("priority_rank"),
                func.min(candidate_pool.c.next_run_at).label("next_run_at"),
                func.min(candidate_pool.c.created_at).label("created_at"),
            )
            .group_by(candidate_pool.c.task_id, candidate_pool.c.site, candidate_pool.c.task_type)
            .subquery()
        )
        return (
            select(
                candidate_rows.c.task_id,
                candidate_rows.c.site,
                candidate_rows.c.task_type,
                candidate_rows.c.source_rank,
                candidate_rows.c.priority_rank,
                candidate_rows.c.next_run_at,
                candidate_rows.c.created_at,
            )
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

    def _sort_candidates_by_runtime_pressure(self, session: Session, candidate_rows: list[Any]) -> list[Any]:
        if not candidate_rows:
            return []

        candidate_sites = {str(row["site"]) for row in candidate_rows if row["site"]}
        candidate_task_types = {str(row["task_type"]) for row in candidate_rows if row["task_type"]}
        running_by_site = self._count_running_tasks_by_site(session, candidate_sites)
        running_by_task_type = self._count_running_tasks_by_task_type(session, candidate_task_types)

        def _sort_key(row: Any) -> tuple:
            site = str(row["site"] or "")
            task_type = str(row["task_type"] or "")
            site_limit = max(1, self.policy.get_site_limit(site))
            task_type_limit = self.policy.get_task_type_limit(task_type)
            site_pressure = running_by_site.get(site, 0) / site_limit
            task_type_pressure = (
                0.0
                if task_type_limit is None
                else running_by_task_type.get(task_type, 0) / max(1, task_type_limit)
            )
            return (
                task_type_pressure,
                site_pressure,
                int(row["source_rank"]),
                -int(row["priority_rank"]),
                row["next_run_at"],
                row["created_at"],
                int(row["task_id"]),
            )

        return sorted(candidate_rows, key=_sort_key)

    def _try_claim_candidate(
        self,
        session: Session,
        *,
        task_id: int,
        worker_id: str,
        now: datetime,
        lease_seconds: int,
    ) -> CrawlTask | None:
        task = session.execute(
            select(CrawlTask)
            .where(
                CrawlTask.id == task_id,
                CrawlTask.status.in_([CrawlTaskStatus.PENDING.value, CrawlTaskStatus.RETRY_WAIT.value]),
                CrawlTask.next_run_at <= now,
                or_(CrawlTask.lease_until.is_(None), CrawlTask.lease_until < now),
            )
            .with_for_update(skip_locked=True),
        ).scalar_one_or_none()
        if task is None:
            return None

        if self._lock_scope(session, scope_type="site", scope_key=task.site) is None:
            return None
        if self._lock_scope(session, scope_type="task_type", scope_key=task.task_type) is None:
            return None

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

    def _get_session(self):
        if self.session_factory is not None:
            return self.session_factory()
        from core.database import get_session
        return get_session()

    def _lock_scope(self, session: Session, *, scope_type: str, scope_key: str) -> CrawlDispatchScope | None:
        CrawlTaskService._ensure_dispatch_scope(session, scope_type=scope_type, scope_key=scope_key)
        scope = session.execute(
            select(CrawlDispatchScope)
            .where(
                CrawlDispatchScope.scope_type == scope_type,
                CrawlDispatchScope.scope_key == scope_key,
            )
            .with_for_update(skip_locked=True),
        ).scalar_one_or_none()
        return scope

    @staticmethod
    def _count_running_tasks(session: Session, *, site: str | None = None, task_type: str | None = None) -> int:
        query = select(func.count(CrawlTask.id)).where(
            CrawlTask.status.in_([CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value]),
        )
        if site is not None:
            query = query.where(CrawlTask.site == site)
        if task_type is not None:
            query = query.where(CrawlTask.task_type == task_type)
        value = session.execute(query).scalar_one()
        return int(value or 0)

    @staticmethod
    def _count_running_tasks_by_site(session: Session, sites: set[str]) -> dict[str, int]:
        if not sites:
            return {}
        rows = session.execute(
            select(CrawlTask.site, func.count(CrawlTask.id))
            .where(
                CrawlTask.status.in_([CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value]),
                CrawlTask.site.in_(list(sites)),
            )
            .group_by(CrawlTask.site),
        ).all()
        return {str(site): int(count or 0) for site, count in rows}

    @staticmethod
    def _count_running_tasks_by_task_type(session: Session, task_types: set[str]) -> dict[str, int]:
        if not task_types:
            return {}
        rows = session.execute(
            select(CrawlTask.task_type, func.count(CrawlTask.id))
            .where(
                CrawlTask.status.in_([CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value]),
                CrawlTask.task_type.in_(list(task_types)),
            )
            .group_by(CrawlTask.task_type),
        ).all()
        return {str(task_type): int(count or 0) for task_type, count in rows}
