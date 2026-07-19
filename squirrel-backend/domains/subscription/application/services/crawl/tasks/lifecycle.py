from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.subscription.application.services.crawl.tasks.clock import database_local_now
from domains.subscription.application.services.crawl.tasks.errors import (
    CrawlTaskNotFoundError,
    CrawlTaskOwnershipError,
    CrawlTaskStateError,
)
from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.domain.models.crawl_task import CrawlTask


def get_owned_task(
    session: Session,
    *,
    task_id: int,
    worker_id: str,
    lease_token: str | None = None,
    now: datetime | None = None,
) -> CrawlTask:
    task = get_task_for_update(session, task_id)
    if not task:
        raise CrawlTaskNotFoundError(f'Crawl task not found: {task_id}')
    if task.worker_id != worker_id:
        raise CrawlTaskOwnershipError(f'Crawl task {task_id} is not owned by worker {worker_id}')
    if task.lease_token is not None and task.lease_token != lease_token:
        raise CrawlTaskOwnershipError(f'Crawl task {task_id} lease token is stale')
    if task.status not in {CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value}:
        raise CrawlTaskOwnershipError(f'Crawl task {task_id} no longer has an active lease')
    if task.lease_until is None or task.lease_until < (now or database_local_now(session)):
        raise CrawlTaskOwnershipError(f'Crawl task {task_id} lease has expired')
    return task


def get_task_for_update(session: Session, task_id: int) -> CrawlTask | None:
    return session.execute(
        select(CrawlTask).where(CrawlTask.id == task_id).with_for_update(),
    ).scalar_one_or_none()


def mark_running(task: CrawlTask, *, now: datetime) -> None:
    task.status = CrawlTaskStatus.RUNNING.value
    task.started_at = task.started_at or now


def mark_succeeded(task: CrawlTask, *, now: datetime) -> None:
    task.status = CrawlTaskStatus.SUCCEEDED.value
    task.finished_at = now
    task.lease_until = None
    task.worker_id = None
    task.lease_token = None
    task.last_error = None
    task.last_error_type = None
    task.dedupe_key = None


def move_to_retry_or_dead(
    task: CrawlTask,
    *,
    now: datetime,
    error_message: str | None,
    error_type: str | None,
    delay_seconds: int,
    retryable: bool = True,
) -> None:
    task.attempt += 1
    task.last_error = error_message
    task.last_error_type = error_type
    task.lease_until = None
    task.worker_id = None
    task.lease_token = None

    if not retryable or task.attempt >= task.max_attempts:
        task.status = CrawlTaskStatus.DEAD.value
        task.finished_at = now
        if task.task_type != 'video_extract' or not task.run_id:
            task.dedupe_key = None
        return

    task.status = CrawlTaskStatus.RETRY_WAIT.value
    task.next_run_at = now + timedelta(seconds=delay_seconds)


def mark_cancelled(task: CrawlTask, *, now: datetime, reason: str) -> None:
    if task.status in {
        CrawlTaskStatus.SUCCEEDED.value,
        CrawlTaskStatus.DEAD.value,
        CrawlTaskStatus.CANCELLED.value,
    }:
        raise CrawlTaskStateError(f'Crawl task {task.id} can not be cancelled from status {task.status}')

    task.status = CrawlTaskStatus.CANCELLED.value
    task.finished_at = now
    task.lease_until = None
    task.worker_id = None
    task.lease_token = None
    task.last_error = reason
    task.last_error_type = CrawlTaskStatus.CANCELLED.value
    if task.task_type != 'video_extract' or not task.run_id:
        task.dedupe_key = None


def replay_dead(task: CrawlTask, *, now: datetime) -> None:
    if task.status != CrawlTaskStatus.DEAD.value:
        raise CrawlTaskStateError(f'Crawl task {task.id} can not be replayed from status {task.status}')

    task.status = CrawlTaskStatus.PENDING.value
    task.attempt = 0
    task.next_run_at = now
    task.started_at = None
    task.finished_at = None
    task.lease_until = None
    task.worker_id = None
    task.lease_token = None
    task.last_error = None
    task.last_error_type = None
