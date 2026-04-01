from __future__ import annotations

import logging
import threading
from datetime import datetime

from core.config import settings
from services.crawl_dispatcher.service import CrawlDispatcherService
from services.crawl_executors.subscription_sync_executor import execute_subscription_sync_task
from services.crawl_executors.video_extract_executor import execute_video_extract_task
from services.crawl_tasks import service as crawl_task_service

logger = logging.getLogger(__name__)


class CrawlWorkerRuntime:
    def __init__(
        self,
        *,
        dispatcher: CrawlDispatcherService | None = None,
        worker_id: str = 'crawl-worker-1',
        lease_seconds: int | None = None,
        retry_delay_seconds: int = 30,
        poll_interval_seconds: float = 1.0,
    ):
        self.dispatcher = dispatcher or CrawlDispatcherService()
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds or settings.CRAWL_WORKER_LEASE_SECONDS
        self.retry_delay_seconds = retry_delay_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def run_once(self) -> bool:
        now = datetime.now()
        crawl_task_service.recover_expired_tasks(now=now, retry_delay_seconds=self.retry_delay_seconds)
        task = self.dispatcher.claim_next(worker_id=self.worker_id, now=now, lease_seconds=self.lease_seconds)
        if not task:
            return False

        try:
            crawl_task_service.start_task(task_id=task.id, worker_id=self.worker_id, now=now)
            self._execute_task(task)
            crawl_task_service.complete_task(task_id=task.id, worker_id=self.worker_id, now=datetime.now())
        except Exception as exc:
            logger.exception("Crawl worker execution failed task_id=%s task_type=%s", task.id, task.task_type)
            crawl_task_service.retry_task(
                task_id=task.id,
                worker_id=self.worker_id,
                error_message=str(exc),
                error_type=type(exc).__name__,
                now=datetime.now(),
                delay_seconds=self.retry_delay_seconds,
            )
        return True

    def run_loop(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            did_work = self.run_once()
            if did_work:
                continue
            stop_event.wait(self.poll_interval_seconds)

    def _execute_task(self, task) -> None:
        if task.task_type == 'video_extract':
            execute_video_extract_task(task)
            return
        if task.task_type == 'subscription_sync':
            execute_subscription_sync_task(task)
            return
        raise ValueError(f'Unsupported crawl task type: {task.task_type}')
