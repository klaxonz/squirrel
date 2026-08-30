from __future__ import annotations

import logging
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import datetime

from domains.subscription.application.services.crawl.tasks.errors import (
    CrawlTaskNotFoundError,
    CrawlTaskOwnershipError,
)
from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService

logger = logging.getLogger(__name__)


@dataclass
class ActiveTaskLease:
    task_id: int
    last_renewed_at: datetime
    lease_token: str | None = None


class CrawlWorkerLeaseTracker:
    def __init__(self, *, worker_id: str, lease_seconds: int, crawl_tasks: CrawlTaskService) -> None:
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self._crawl_tasks = crawl_tasks
        self.futures: set[Future] = set()
        self.active_leases: dict[Future, ActiveTaskLease] = {}
    @property
    def active_count(self) -> int:
        return len(self.futures)

    def track(self, future: Future, *, task_id: int, now: datetime, lease_token: str | None = None) -> None:
        self.futures.add(future)
        self.active_leases[future] = ActiveTaskLease(
            task_id=task_id,
            lease_token=lease_token,
            last_renewed_at=now,
        )

    def reap_completed_futures(self) -> None:
        completed = {future for future in self.futures if future.done()}
        for future in completed:
            try:
                future.result()
            except Exception:  # worker-slot boundary; a failed slot must not terminate the dispatcher loop
                logger.exception('Crawl worker slot terminated unexpectedly')
            finally:
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
                renew_kwargs = {
                    'task_id': lease.task_id,
                    'worker_id': self.worker_id,
                    'lease_seconds': self.lease_seconds,
                }
                if lease.lease_token:
                    renew_kwargs['lease_token'] = lease.lease_token
                self._crawl_tasks.renew_task_lease(**renew_kwargs)
            except (CrawlTaskNotFoundError, CrawlTaskOwnershipError):
                logger.warning(
                    'Stop renewing unavailable crawl task lease: task_id=%s worker_id=%s',
                    lease.task_id,
                    self.worker_id,
                )
                self.active_leases.pop(future, None)
                continue
            except Exception:
                logger.exception(
                    'Failed to renew crawl task lease; will retry: task_id=%s worker_id=%s',
                    lease.task_id,
                    self.worker_id,
                )
                continue
            lease.last_renewed_at = now
