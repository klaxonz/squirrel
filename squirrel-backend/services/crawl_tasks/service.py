from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_session
from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from services import video_extraction_projection_service
from services.crawl_tasks.errors import CrawlTaskNotFoundError, CrawlTaskOwnershipError, CrawlTaskStateError
from services.crawl_tasks.models import CrawlJobStatus, CrawlTaskStatus
from services.crawl_tasks.task_types import is_subscription_sync_task_type, subscription_sync_task_types

ACTIVE_TASK_STATUSES = [
    CrawlTaskStatus.PENDING.value,
    CrawlTaskStatus.LEASED.value,
    CrawlTaskStatus.RUNNING.value,
    CrawlTaskStatus.RETRY_WAIT.value,
]
FAILED_TASK_STATUSES = [
    CrawlTaskStatus.DEAD.value,
    CrawlTaskStatus.CANCELLED.value,
]


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
            self._ensure_dispatch_scope(session, scope_type="site", scope_key=site)
            self._ensure_dispatch_scope(session, scope_type="task_type", scope_key=task_type)
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
            self._refresh_video_extraction_projection(session, task)
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
            self._ensure_dispatch_scope(session, scope_type="site", scope_key=site)
            self._ensure_dispatch_scope(session, scope_type="task_type", scope_key=task_type)
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
            self._refresh_video_extraction_projection(session, task)
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
        priority_order = case(
            (CrawlTask.priority == "manual", 3),
            (CrawlTask.priority == "normal", 2),
            (CrawlTask.priority == "low", 1),
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

        with self.session_factory() as session:
            task = session.execute(query).scalar_one_or_none()

            if not task:
                return None

            task.status = CrawlTaskStatus.LEASED.value
            task.worker_id = worker_id
            task.lease_until = now + timedelta(seconds=lease_seconds)
            self._refresh_video_extraction_projection(session, task)
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
            task = self._get_owned_task(session, task_id=task_id, worker_id=worker_id)
            task.lease_until = now + timedelta(seconds=lease_seconds)
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
            task = self._get_owned_task(session, task_id=task_id, worker_id=worker_id)
            task.status = CrawlTaskStatus.RUNNING.value
            task.started_at = task.started_at or now
            self._refresh_job_status(session, job_id=task.job_id, now=now)
            self._refresh_video_extraction_projection(session, task)
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
            task = self._get_owned_task(session, task_id=task_id, worker_id=worker_id)
            task.status = CrawlTaskStatus.SUCCEEDED.value
            task.finished_at = now
            task.lease_until = None
            task.worker_id = None
            task.last_error = None
            task.last_error_type = None
            self._refresh_job_status(session, job_id=task.job_id, now=now)
            self._refresh_video_extraction_projection(session, task)
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
            task = self._get_owned_task(session, task_id=task_id, worker_id=worker_id)
            self._move_task_to_retry_or_dead(
                task,
                now=now,
                error_message=error_message,
                error_type=error_type,
                delay_seconds=delay_seconds,
            )
            self._refresh_job_status(session, job_id=task.job_id, now=now)
            self._refresh_video_extraction_projection(session, task)
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
                raise CrawlTaskNotFoundError(f"Crawl task not found: {task_id}")
            if task.status in {
                CrawlTaskStatus.SUCCEEDED.value,
                CrawlTaskStatus.DEAD.value,
                CrawlTaskStatus.CANCELLED.value,
            }:
                raise CrawlTaskStateError(f"Crawl task {task_id} can not be cancelled from status {task.status}")

            task.status = CrawlTaskStatus.CANCELLED.value
            task.finished_at = now
            task.lease_until = None
            task.worker_id = None
            task.last_error = reason
            task.last_error_type = CrawlTaskStatus.CANCELLED.value
            self._refresh_job_status(session, job_id=task.job_id, now=now)
            self._refresh_video_extraction_projection(session, task)
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
                raise CrawlTaskNotFoundError(f"Crawl task not found: {task_id}")
            if task.status != CrawlTaskStatus.DEAD.value:
                raise CrawlTaskStateError(f"Crawl task {task_id} can not be replayed from status {task.status}")

            task.status = CrawlTaskStatus.PENDING.value
            task.attempt = 0
            task.next_run_at = now
            task.started_at = None
            task.finished_at = None
            task.lease_until = None
            task.worker_id = None
            task.last_error = None
            task.last_error_type = None
            self._refresh_job_status(session, job_id=task.job_id, now=now)
            self._refresh_video_extraction_projection(session, task)
            session.flush()
            return task

    def recover_expired_tasks(self, *, now: datetime | None = None, retry_delay_seconds: int = 30) -> int:
        now = now or datetime.now()

        with self.session_factory() as session:
            tasks = session.execute(
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
            ).scalars().all()

            touched_job_ids: set[int] = set()
            for task in tasks:
                self._move_task_to_retry_or_dead(
                    task,
                    now=now,
                    error_message="lease_expired",
                    error_type="lease_expired",
                    delay_seconds=retry_delay_seconds,
                )
                touched_job_ids.add(task.job_id)
                self._refresh_video_extraction_projection(session, task)

            for job_id in touched_job_ids:
                self._refresh_job_status(session, job_id=job_id, now=now)

            session.flush()
            return len(tasks)

    def count_pending_video_tasks_for_subscription(self, subscription_id: int) -> int:
        with self.session_factory() as session:
            value = session.execute(
                select(func.count(CrawlTask.id)).where(
                    CrawlTask.task_type == "video_extract",
                    CrawlTask.subscription_id == subscription_id,
                    CrawlTask.status.in_(ACTIVE_TASK_STATUSES),
                ),
            ).scalar_one()
        return int(value or 0)

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
        with self.session_factory() as session:
            tasks = session.execute(
                select(CrawlTask)
                .where(
                    CrawlTask.task_type == "video_extract",
                    CrawlTask.status.in_(ACTIVE_TASK_STATUSES),
                ),
            ).scalars().all()
        counts: dict[int, int] = {}
        for task in tasks:
            sync_state_id = (task.payload or {}).get("sync_state_id")
            if sync_state_id in (None, ""):
                continue
            counts[int(sync_state_id)] = counts.get(int(sync_state_id), 0) + 1
        return counts

    def summarize_video_task_states_by_sync_state(self) -> dict[int, dict[str, object]]:
        with self.session_factory() as session:
            tasks = session.execute(
                select(CrawlTask).where(CrawlTask.task_type == "video_extract"),
            ).scalars().all()

        summary: dict[int, dict[str, object]] = {}
        for task in tasks:
            sync_state_id = (task.payload or {}).get("sync_state_id")
            if sync_state_id in (None, ""):
                continue

            key = int(sync_state_id)
            bucket = summary.setdefault(
                key,
                {
                    "active_count": 0,
                    "failed_count": 0,
                    "last_error": None,
                    "last_error_at": datetime.min,
                },
            )

            if task.status in ACTIVE_TASK_STATUSES:
                bucket["active_count"] = int(bucket["active_count"]) + 1
                continue

            if task.status not in FAILED_TASK_STATUSES:
                continue

            bucket["failed_count"] = int(bucket["failed_count"]) + 1
            error_at = task.updated_at or task.finished_at or task.created_at or datetime.min
            if error_at >= bucket["last_error_at"]:
                bucket["last_error_at"] = error_at
                bucket["last_error"] = task.last_error or task.last_error_type or "video_extract_failed"

        for bucket in summary.values():
            bucket.pop("last_error_at", None)

        return summary

    def list_active_subscription_sync_state_ids(self) -> set[int]:
        with self.session_factory() as session:
            tasks = session.execute(
                select(CrawlTask)
                .where(
                    CrawlTask.task_type.in_(subscription_sync_task_types()),
                    CrawlTask.status.in_(ACTIVE_TASK_STATUSES),
                ),
            ).scalars().all()
        state_ids: set[int] = set()
        for task in tasks:
            sync_state_id = (task.payload or {}).get("sync_state_id")
            if sync_state_id in (None, ""):
                continue
            state_ids.add(int(sync_state_id))
        return state_ids

    @staticmethod
    def _get_owned_task(session: Session, *, task_id: int, worker_id: str) -> CrawlTask:
        task = session.get(CrawlTask, task_id)
        if not task:
            raise CrawlTaskNotFoundError(f"Crawl task not found: {task_id}")
        if task.worker_id != worker_id:
            raise CrawlTaskOwnershipError(f"Crawl task {task_id} is not owned by worker {worker_id}")
        return task

    def _move_task_to_retry_or_dead(
        self,
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
            self._reconcile_subscription_sync_state_for_retry(
                task,
                now=now,
                retryable=False,
                error_message=error_message,
            )
            return

        task.status = CrawlTaskStatus.RETRY_WAIT.value
        task.next_run_at = now + timedelta(seconds=delay_seconds)
        self._reconcile_subscription_sync_state_for_retry(
            task,
            now=now,
            retryable=True,
            error_message=error_message,
        )

    @staticmethod
    def _refresh_job_status(session: Session, *, job_id: int, now: datetime) -> None:
        job = session.get(CrawlJob, job_id)
        if not job:
            return

        tasks = session.execute(
            select(CrawlTask).where(CrawlTask.job_id == job_id).order_by(CrawlTask.id.asc()),
        ).scalars().all()
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
                task.status in {
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
            job.error_message = "cancelled"
        elif dead_count == len(tasks):
            job.status = CrawlJobStatus.FAILED.value
            job.error_message = "job_failed"
        elif dead_count or cancelled_count:
            job.status = CrawlJobStatus.PARTIAL_FAILED.value
            job.error_message = "partial_failed"
        elif succeeded_count == len(tasks):
            job.status = CrawlJobStatus.SUCCEEDED.value
            job.error_message = None
        else:
            job.status = CrawlJobStatus.PENDING.value
            job.error_message = None

        finished_at_values = [task.finished_at for task in tasks if task.finished_at]
        job.finished_at = max(finished_at_values) if finished_at_values else now

    @staticmethod
    def _ensure_dispatch_scope(session: Session, *, scope_type: str, scope_key: str) -> CrawlDispatchScope:
        scope = session.execute(
            select(CrawlDispatchScope).where(
                CrawlDispatchScope.scope_type == scope_type,
                CrawlDispatchScope.scope_key == scope_key,
            ),
        ).scalar_one_or_none()
        if scope:
            return scope

        with session.begin_nested():
            scope = CrawlDispatchScope(scope_type=scope_type, scope_key=scope_key)
            session.add(scope)
            try:
                session.flush()
                return scope
            except IntegrityError:
                pass

        scope = session.execute(
            select(CrawlDispatchScope).where(
                CrawlDispatchScope.scope_type == scope_type,
                CrawlDispatchScope.scope_key == scope_key,
            ),
        ).scalar_one()
        return scope

    def _reconcile_subscription_sync_state_for_retry(
        self,
        task: CrawlTask,
        *,
        now: datetime,
        retryable: bool,
        error_message: str | None,
    ) -> None:
        if not is_subscription_sync_task_type(task.task_type):
            return

        payload = task.payload or {}
        sync_state_id = payload.get("sync_state_id")
        if sync_state_id in (None, ""):
            return

        try:
            sync_state_id = int(sync_state_id)
        except (TypeError, ValueError):
            return

        from services import subscription_sync_state_service

        subscription_sync_state_service.reconcile_task_retry_state(
            sync_state_id,
            payload.get("queue_token"),
            now=now,
            retryable=retryable,
            error_message=error_message,
            run_id=payload.get("run_id"),
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
            trigger=payload.get("trigger"),
        )

    @staticmethod
    def _refresh_video_extraction_projection(session: Session, task: CrawlTask) -> None:
        video_extraction_projection_service.refresh_projection_for_task(task, session=session)


_default = CrawlTaskService()
create_job = _default.create_job
create_task = _default.create_task
create_job_with_task = _default.create_job_with_task
claim_next_task = _default.claim_next_task
renew_task_lease = _default.renew_task_lease
start_task = _default.start_task
complete_task = _default.complete_task
retry_task = _default.retry_task
cancel_task = _default.cancel_task
replay_dead_task = _default.replay_dead_task
recover_expired_tasks = _default.recover_expired_tasks
count_pending_video_tasks_for_subscription = _default.count_pending_video_tasks_for_subscription
clear_task_dedupe_key = _default.clear_task_dedupe_key
count_pending_video_tasks_by_sync_state = _default.count_pending_video_tasks_by_sync_state
summarize_video_task_states_by_sync_state = _default.summarize_video_task_states_by_sync_state
list_active_subscription_sync_state_ids = _default.list_active_subscription_sync_state_ids
_ensure_dispatch_scope = _default._ensure_dispatch_scope
_refresh_video_extraction_projection = _default._refresh_video_extraction_projection
