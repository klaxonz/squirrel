from __future__ import annotations

import logging
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import datetime

from domains.subscription.application.services.crawl.tasks import service as crawl_task_service
from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskNotFoundError, CrawlTaskOwnershipError

logger = logging.getLogger(__name__)


@dataclass
class ActiveTaskLease:
    task_id: int
    last_renewed_at: datetime


class CrawlWorkerLeaseTracker:
    def __init__(self, *, worker_id: str, lease_seconds: int) -> None:
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.futures: set[Future] = set()
        self.active_leases: dict[Future, ActiveTaskLease] = {}

    @property
    def active_count(self) -> int:
        return len(self.futures)

    def track(self, future: Future, *, task_id: int, now: datetime) -> None:
        self.futures.add(future)
        self.active_leases[future] = ActiveTaskLease(task_id=task_id, last_renewed_at=now)

    def reap_completed_futures(self) -> None:
        completed = {future for future in self.futures if future.done()}
        for future in completed:
            future.result()
            self.active_leases.pop(future, None)
        self.futures.difference_update(completed)

    def renew_active_leases(self, *, now: datetime) -> None:
        for future in tuple(self.futures):
            if future.done():
                continue
            lease = self.active_leases.get(future)
            if lease is None:
                continue
            renew_after = max(0.25, self.lease_seconds / 3)
            if (now - lease.last_renewed_at).total_seconds() < renew_after:
                continue
            try:
                crawl_task_service.renew_task_lease(
                    task_id=lease.task_id,
                    worker_id=self.worker_id,
                    now=now,
                    lease_seconds=self.lease_seconds,
                )
            except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
                logger.warning(
                    'Stop renewing crawl task lease because ownership is lost: task_id=%s worker_id=%s',
                    lease.task_id,
                    self.worker_id,
                )
                self.active_leases.pop(future, None)
                continue
            lease.last_renewed_at = now
