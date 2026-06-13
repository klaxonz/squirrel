from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.crawl_task import CrawlTask
from services.crawl.tasks.errors import CrawlTaskNotFoundError, CrawlTaskOwnershipError, CrawlTaskStateError
from services.crawl.tasks.models import CrawlTaskStatus


def get_owned_task(session: Session, *, task_id: int, worker_id: str) -> CrawlTask:
    task = session.get(CrawlTask, task_id)
    if not task:
        raise CrawlTaskNotFoundError(f'Crawl task not found: {task_id}')
    if task.worker_id != worker_id:
        raise CrawlTaskOwnershipError(f'Crawl task {task_id} is not owned by worker {worker_id}')
    return task


def mark_running(task: CrawlTask, *, now: datetime) -> None:
    task.status = CrawlTaskStatus.RUNNING.value
    task.started_at = task.started_at or now


def mark_succeeded(task: CrawlTask, *, now: datetime) -> None:
    task.status = CrawlTaskStatus.SUCCEEDED.value
    task.finished_at = now
    task.lease_until = None
    task.worker_id = None
    task.last_error = None
    task.last_error_type = None


def move_to_retry_or_dead(
    task: CrawlTask,
    *,
    now: datetime,
    error_message: str | None,
    error_type: str | None,
    delay_seconds: int,
) -> None:
    task.attempt += 1
    task.last_error = error_message
    task.last_error_type = error_type
    task.lease_until = None
    task.worker_id = None

    if task.attempt >= task.max_attempts:
        task.status = CrawlTaskStatus.DEAD.value
        task.finished_at = now
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
    task.last_error = reason
    task.last_error_type = CrawlTaskStatus.CANCELLED.value


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
    task.last_error = None
    task.last_error_type = None
