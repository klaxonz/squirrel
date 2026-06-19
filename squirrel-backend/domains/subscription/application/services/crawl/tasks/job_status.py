from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.subscription.application.services.crawl.tasks.models import CrawlJobStatus, CrawlTaskStatus
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask


def refresh_job_status(session: Session, *, job_id: int, now: datetime) -> None:
    job = session.get(CrawlJob, job_id)
    if not job:
        return

    tasks = (
        session.execute(
            select(CrawlTask).where(CrawlTask.job_id == job_id).order_by(CrawlTask.id.asc()),
        )
        .scalars()
        .all()
    )
    if not tasks:
        return

    started_at_values = [task.started_at for task in tasks if task.started_at]
    job.started_at = min(started_at_values) if started_at_values else None

    active_statuses = {
        CrawlTaskStatus.PENDING.value,
        CrawlTaskStatus.LEASED.value,
        CrawlTaskStatus.RUNNING.value,
        CrawlTaskStatus.RETRY_WAIT.value,
    }
    active_tasks = [task for task in tasks if task.status in active_statuses]
    if active_tasks:
        has_started_work = any(
            task.status
            in {
                CrawlTaskStatus.LEASED.value,
                CrawlTaskStatus.RUNNING.value,
                CrawlTaskStatus.RETRY_WAIT.value,
            }
            or task.started_at is not None
            for task in tasks
        )
        job.status = CrawlJobStatus.RUNNING.value if has_started_work else CrawlJobStatus.PENDING.value
        job.finished_at = None
        if job.status in {CrawlJobStatus.PENDING.value, CrawlJobStatus.RUNNING.value}:
            job.error_message = None
        return

    succeeded_count = sum(1 for task in tasks if task.status == CrawlTaskStatus.SUCCEEDED.value)
    dead_count = sum(1 for task in tasks if task.status == CrawlTaskStatus.DEAD.value)
    cancelled_count = sum(1 for task in tasks if task.status == CrawlTaskStatus.CANCELLED.value)

    if cancelled_count == len(tasks):
        job.status = CrawlJobStatus.CANCELLED.value
        job.error_message = 'cancelled'
    elif dead_count == len(tasks):
        job.status = CrawlJobStatus.FAILED.value
        job.error_message = 'job_failed'
    elif dead_count or cancelled_count:
        job.status = CrawlJobStatus.PARTIAL_FAILED.value
        job.error_message = 'partial_failed'
    elif succeeded_count == len(tasks):
        job.status = CrawlJobStatus.SUCCEEDED.value
        job.error_message = None
    else:
        job.status = CrawlJobStatus.PENDING.value
        job.error_message = None

    finished_at_values = [task.finished_at for task in tasks if task.finished_at]
    job.finished_at = max(finished_at_values) if finished_at_values else now
