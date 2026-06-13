from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select

from infrastructure.database.session import get_session
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.application.services.crawl.tasks import lease, lifecycle
from domains.subscription.application.services.crawl.tasks import summary as task_summary
from domains.subscription.application.services.crawl.tasks.dispatch_scope import ensure_dispatch_scope
from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskNotFoundError
from domains.subscription.application.services.crawl.tasks.job_status import refresh_job_status
from domains.subscription.application.services.crawl.tasks.models import CrawlJobStatus


class CrawlTaskService:
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session

    def create_job(
        self,
        *,
        job_type: str,
        source_type: str,
        site: str | None,
        subscription_id: int | None = None,
        priority: str = "normal",
        status: str = CrawlJobStatus.PENDING.value,
        trace_id: str | None = None,
        payload: dict | None = None,
    ) -> CrawlJob:
        with self.session_factory() as session:
            job = CrawlJob(
                job_type=job_type,
                source_type=source_type,
                site=site,
                subscription_id=subscription_id,
                priority=priority,
                status=status,
                trace_id=trace_id,
                payload=payload or {},
            )
            session.add(job)
            session.flush()
            return job

    def create_task(
        self,
        *,
        job_id: int,
        task_type: str,
        site: str,
        priority: str = "normal",
        payload: dict | None = None,
        dedupe_key: str | None = None,
        parent_task_id: int | None = None,
        subscription_id: int | None = None,
        video_id: int | None = None,
        video_url: str | None = None,
        trace_id: str | None = None,
        max_attempts: int = 3,
        next_run_at: datetime | None = None,
    ) -> CrawlTask:
        with self.session_factory() as session:
            ensure_dispatch_scope(session, scope_type="site", scope_key=site)
            ensure_dispatch_scope(session, scope_type="task_type", scope_key=task_type)
            task = CrawlTask(
                job_id=job_id,
                parent_task_id=parent_task_id,
                task_type=task_type,
                site=site,
                subscription_id=subscription_id,
                video_id=video_id,
                video_url=video_url,
                priority=priority,
                payload=payload or {},
                dedupe_key=dedupe_key,
                trace_id=trace_id,
                max_attempts=max_attempts,
                next_run_at=next_run_at or datetime.now(),
            )
            session.add(task)
            session.flush()
            return task

    def create_job_with_task(
        self,
        *,
        job_type: str,
        source_type: str,
        site: str,
        task_type: str,
        payload: dict,
        subscription_id: int | None = None,
        priority: str = "normal",
        dedupe_key: str | None = None,
        parent_task_id: int | None = None,
        video_id: int | None = None,
        video_url: str | None = None,
        trace_id: str | None = None,
        max_attempts: int = 3,
        next_run_at: datetime | None = None,
    ) -> tuple[CrawlJob, CrawlTask]:
        with self.session_factory() as session:
            ensure_dispatch_scope(session, scope_type="site", scope_key=site)
            ensure_dispatch_scope(session, scope_type="task_type", scope_key=task_type)
            job = CrawlJob(
                job_type=job_type,
                source_type=source_type,
                site=site,
                subscription_id=subscription_id,
                priority=priority,
                status=CrawlJobStatus.PENDING.value,
                trace_id=trace_id,
                payload=payload,
            )
            session.add(job)
            session.flush()

            task = CrawlTask(
                job_id=job.id,
                parent_task_id=parent_task_id,
                task_type=task_type,
                site=site,
                subscription_id=subscription_id,
                video_id=video_id,
                video_url=video_url,
                priority=priority,
                payload=payload,
                dedupe_key=dedupe_key,
                trace_id=trace_id,
                max_attempts=max_attempts,
                next_run_at=next_run_at or datetime.now(),
            )
            session.add(task)
            session.flush()
            return job, task

    def claim_next_task(
        self,
        *,
        worker_id: str,
        now: datetime | None = None,
        lease_seconds: int = 60,
        allowed_sites: Sequence[str] | None = None,
        allowed_task_types: Sequence[str] | None = None,
    ) -> CrawlTask | None:
        now = now or datetime.now()

        with self.session_factory() as session:
            task = lease.claim_next_task(
                session,
                worker_id=worker_id,
                now=now,
                lease_seconds=lease_seconds,
                allowed_sites=allowed_sites,
                allowed_task_types=allowed_task_types,
            )
            session.flush()
            return task

    def renew_task_lease(
        self,
        *,
        task_id: int,
        worker_id: str,
        now: datetime | None = None,
        lease_seconds: int = 60,
    ) -> CrawlTask | None:
        now = now or datetime.now()

        with self.session_factory() as session:
            task = lifecycle.get_owned_task(session, task_id=task_id, worker_id=worker_id)
            lease.renew_lease(task, now=now, lease_seconds=lease_seconds)
            session.flush()
            return task

    def start_task(
        self,
        *,
        task_id: int,
        worker_id: str,
        now: datetime | None = None,
    ) -> CrawlTask:
        now = now or datetime.now()

        with self.session_factory() as session:
            task = lifecycle.get_owned_task(session, task_id=task_id, worker_id=worker_id)
            lifecycle.mark_running(task, now=now)
            refresh_job_status(session, job_id=task.job_id, now=now)
            session.flush()
            return task

    def complete_task(
        self,
        *,
        task_id: int,
        worker_id: str,
        now: datetime | None = None,
    ) -> CrawlTask:
        now = now or datetime.now()

        with self.session_factory() as session:
            task = lifecycle.get_owned_task(session, task_id=task_id, worker_id=worker_id)
            lifecycle.mark_succeeded(task, now=now)
            refresh_job_status(session, job_id=task.job_id, now=now)
            session.flush()
            return task

    def retry_task(
        self,
        *,
        task_id: int,
        worker_id: str,
        error_message: str | None,
        error_type: str | None,
        now: datetime | None = None,
        delay_seconds: int = 30,
    ) -> CrawlTask:
        now = now or datetime.now()

        with self.session_factory() as session:
            task = lifecycle.get_owned_task(session, task_id=task_id, worker_id=worker_id)
            lifecycle.move_to_retry_or_dead(
                task,
                now=now,
                error_message=error_message,
                error_type=error_type,
                delay_seconds=delay_seconds,
            )
            refresh_job_status(session, job_id=task.job_id, now=now)
            session.flush()
            return task

    def cancel_task(
        self,
        *,
        task_id: int,
        now: datetime | None = None,
        reason: str = "cancelled",
    ) -> CrawlTask:
        now = now or datetime.now()

        with self.session_factory() as session:
            task = session.get(CrawlTask, task_id)
            if not task:
                raise CrawlTaskNotFoundError(f'Crawl task not found: {task_id}')
            lifecycle.mark_cancelled(task, now=now, reason=reason)
            refresh_job_status(session, job_id=task.job_id, now=now)
            session.flush()
            return task

    def replay_dead_task(
        self,
        *,
        task_id: int,
        now: datetime | None = None,
    ) -> CrawlTask:
        now = now or datetime.now()

        with self.session_factory() as session:
            task = session.get(CrawlTask, task_id)
            if not task:
                raise CrawlTaskNotFoundError(f'Crawl task not found: {task_id}')
            lifecycle.replay_dead(task, now=now)
            refresh_job_status(session, job_id=task.job_id, now=now)
            session.flush()
            return task

    def recover_expired_tasks(self, *, now: datetime | None = None, retry_delay_seconds: int = 30) -> list[CrawlTask]:
        now = now or datetime.now()

        with self.session_factory() as session:
            tasks = lease.list_expired_leased_tasks(session, now=now)

            touched_job_ids: set[int] = set()
            for task in tasks:
                lifecycle.move_to_retry_or_dead(
                    task,
                    now=now,
                    error_message='lease_expired',
                    error_type='lease_expired',
                    delay_seconds=retry_delay_seconds,
                )
                touched_job_ids.add(task.job_id)

            for job_id in touched_job_ids:
                refresh_job_status(session, job_id=job_id, now=now)

            session.flush()
            return tasks

    def count_pending_video_tasks_for_subscription(self, subscription_id: int) -> int:
        return task_summary.count_pending_video_tasks_for_subscription(self.session_factory, subscription_id)

    def clear_task_dedupe_key(self, dedupe_key: str) -> int:
        with self.session_factory() as session:
            tasks = session.execute(
                select(CrawlTask).where(CrawlTask.dedupe_key == dedupe_key),
            ).scalars().all()
            for task in tasks:
                task.dedupe_key = None
            session.flush()
            return len(tasks)

    def count_pending_video_tasks_by_sync_state(self) -> dict[int, int]:
        return task_summary.count_pending_video_tasks_by_sync_state(self.session_factory)

    def summarize_video_task_states_by_sync_state(self) -> dict[int, dict[str, object]]:
        return task_summary.summarize_video_task_states_by_sync_state(self.session_factory)

    def list_active_subscription_sync_state_ids(self) -> set[int]:
        return task_summary.list_active_subscription_sync_state_ids(self.session_factory)


crawl_task_service = CrawlTaskService()
create_job = crawl_task_service.create_job
create_task = crawl_task_service.create_task
create_job_with_task = crawl_task_service.create_job_with_task
claim_next_task = crawl_task_service.claim_next_task
renew_task_lease = crawl_task_service.renew_task_lease
start_task = crawl_task_service.start_task
complete_task = crawl_task_service.complete_task
retry_task = crawl_task_service.retry_task
cancel_task = crawl_task_service.cancel_task
replay_dead_task = crawl_task_service.replay_dead_task
recover_expired_tasks = crawl_task_service.recover_expired_tasks
count_pending_video_tasks_for_subscription = crawl_task_service.count_pending_video_tasks_for_subscription
clear_task_dedupe_key = crawl_task_service.clear_task_dedupe_key
count_pending_video_tasks_by_sync_state = crawl_task_service.count_pending_video_tasks_by_sync_state
summarize_video_task_states_by_sync_state = crawl_task_service.summarize_video_task_states_by_sync_state
list_active_subscription_sync_state_ids = crawl_task_service.list_active_subscription_sync_state_ids
