from datetime import datetime

from domains.subscription.application.services.core.update.task_progress_service import (
    SubscriptionSyncTaskProgressService,
)
from domains.subscription.domain.models.crawl_task import CrawlTask


class _FakeLifecycle:
    def __init__(self):
        self.calls = []

    def record_task_retry_transition(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def test_record_retry_transition_requeues_retry_wait_subscription_task():
    lifecycle = _FakeLifecycle()
    now = datetime(2026, 4, 2, 12, 0, 0)
    task = CrawlTask(
        task_type="subscription_sync_incremental",
        status="retry_wait",
        payload={
            "sync_state_id": 1749,
            "queue_token": "queue-token-1",
            "run_id": "run-1",
            "request_id": "req-1",
            "trace_id": "trace-1",
            "trigger": "scheduled",
        },
    )

    SubscriptionSyncTaskProgressService(lifecycle).record_retry_transition(
        task,
        now=now,
        error_message="lease_expired",
    )

    assert lifecycle.calls == [
        (
            (1749, "queue-token-1"),
            {
                "now": now,
                "retryable": True,
                "error_message": "lease_expired",
                "run_id": "run-1",
                "request_id": "req-1",
                "trace_id": "trace-1",
                "trigger": "scheduled",
            },
        ),
    ]


def test_record_retry_transition_fails_dead_subscription_task():
    lifecycle = _FakeLifecycle()
    now = datetime(2026, 4, 2, 12, 0, 0)
    task = CrawlTask(
        task_type="subscription_sync_full",
        status="dead",
        payload={
            "sync_state_id": "1750",
            "queue_token": "queue-token-2",
            "run_id": "run-2",
            "request_id": "req-2",
            "trace_id": "trace-2",
            "trigger": "manual",
        },
    )

    SubscriptionSyncTaskProgressService(lifecycle).record_retry_transition(
        task,
        now=now,
        error_message="boom",
    )

    assert lifecycle.calls == [
        (
            (1750, "queue-token-2"),
            {
                "now": now,
                "retryable": False,
                "error_message": "boom",
                "run_id": "run-2",
                "request_id": "req-2",
                "trace_id": "trace-2",
                "trigger": "manual",
            },
        ),
    ]


def test_record_retry_transition_ignores_non_subscription_task():
    lifecycle = _FakeLifecycle()
    task = CrawlTask(task_type="video_extract", status="retry_wait", payload={"sync_state_id": 1})

    SubscriptionSyncTaskProgressService(lifecycle).record_retry_transition(
        task,
        now=datetime(2026, 4, 2, 12, 0, 0),
        error_message="boom",
    )

    assert lifecycle.calls == []
