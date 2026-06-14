from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.domain.models.crawl_task import CrawlTask


def claim_next_task(
    session: Session,
    *,
    worker_id: str,
    now: datetime,
    lease_seconds: int,
    allowed_sites: Sequence[str] | None,
    allowed_task_types: Sequence[str] | None,
) -> CrawlTask | None:
    priority_order = case(
        (CrawlTask.priority == 'manual', 3),
        (CrawlTask.priority == 'normal', 2),
        (CrawlTask.priority == 'low', 1),
        else_=0,
    )
    query = (
        select(CrawlTask)
        .where(
            CrawlTask.status.in_(
                [
                    CrawlTaskStatus.PENDING.value,
                    CrawlTaskStatus.RETRY_WAIT.value,
                ],
            ),
            CrawlTask.next_run_at <= now,
            or_(CrawlTask.lease_until.is_(None), CrawlTask.lease_until < now),
        )
        .order_by(priority_order.desc(), CrawlTask.next_run_at.asc(), CrawlTask.created_at.asc(), CrawlTask.id.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )

    if allowed_sites:
        query = query.where(CrawlTask.site.in_(list(allowed_sites)))
    if allowed_task_types:
        query = query.where(CrawlTask.task_type.in_(list(allowed_task_types)))

    task = session.execute(query).scalar_one_or_none()
    if not task:
        return None

    assign_lease(task, worker_id=worker_id, now=now, lease_seconds=lease_seconds)
    return task


def assign_lease(task: CrawlTask, *, worker_id: str, now: datetime, lease_seconds: int) -> None:
    task.status = CrawlTaskStatus.LEASED.value
    task.worker_id = worker_id
    task.lease_until = now + timedelta(seconds=lease_seconds)


def renew_lease(task: CrawlTask, *, now: datetime, lease_seconds: int) -> None:
    task.lease_until = now + timedelta(seconds=lease_seconds)


def list_expired_leased_tasks(session: Session, *, now: datetime) -> list[CrawlTask]:
    return list(
        session.execute(
            select(CrawlTask)
            .where(
                CrawlTask.status.in_(
                    [
                        CrawlTaskStatus.LEASED.value,
                        CrawlTaskStatus.RUNNING.value,
                    ],
                ),
                CrawlTask.lease_until.is_not(None),
                CrawlTask.lease_until < now,
            )
            .order_by(CrawlTask.lease_until.asc(), CrawlTask.id.asc()),
        )
        .scalars()
        .all(),
    )
