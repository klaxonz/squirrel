import sys
import threading
import time
from concurrent.futures import Future
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskOwnershipError
from domains.subscription.domain.models.crawl_task import CrawlTask
from workers.scheduling.workers.leases import ActiveTaskLease
from workers.scheduling.workers.runtime import CrawlWorkerRuntime


def _noop_runtime(**kwargs):
    kwargs.setdefault(
        "subscription_task_progress",
        SimpleNamespace(record_retry_transition=lambda *args, **kwargs: None),
    )
    return CrawlWorkerRuntime(
        **kwargs,
    )


def test_run_once_executes_video_extract_task(monkeypatch):
    calls = []
    task = CrawlTask(id=1, job_id=1, task_type="video_extract", site="youtube.com", payload={})
    runtime = _noop_runtime(
        dispatcher=SimpleNamespace(claim_next=lambda **kwargs: task),
        worker_id="worker-1",
        lease_seconds=60,
        retry_delay_seconds=30,
    )

    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.recover_expired_tasks",
        lambda now=None, retry_delay_seconds=30: [],
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.start_task",
        lambda task_id, worker_id, now=None: calls.append(("start", task_id, worker_id)) or task,
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.execute_video_extract_task",
        lambda current_task: calls.append(("video", current_task.id)),
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.complete_task",
        lambda task_id, worker_id, now=None: calls.append(("complete", task_id, worker_id)) or task,
    )

    ran = runtime.run_once()

    assert ran is True
    assert calls == [
        ("start", 1, "worker-1"),
        ("video", 1),
        ("complete", 1, "worker-1"),
    ]


def test_run_once_executes_legacy_subscription_sync_task_type(monkeypatch):
    calls = []
    task = CrawlTask(
        id=2,
        job_id=1,
        task_type="subscription_sync",
        site="bilibili.com",
        payload={"subscription_id": 10, "url": "https://space.bilibili.com/42"},
    )
    runtime = _noop_runtime(
        dispatcher=SimpleNamespace(claim_next=lambda **kwargs: task),
        worker_id="worker-1",
        lease_seconds=60,
        retry_delay_seconds=30,
    )

    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.recover_expired_tasks",
        lambda now=None, retry_delay_seconds=30: [],
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.start_task",
        lambda task_id, worker_id, now=None: calls.append(("start", task_id, worker_id)) or task,
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.execute_subscription_sync_task",
        lambda current_task: calls.append(("sync", current_task.id, current_task.task_type)),
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.complete_task",
        lambda task_id, worker_id, now=None: calls.append(("complete", task_id, worker_id)) or task,
    )

    ran = runtime.run_once()

    assert ran is True
    assert calls == [
        ("start", 2, "worker-1"),
        ("sync", 2, "subscription_sync"),
        ("complete", 2, "worker-1"),
    ]


def test_run_once_executes_full_subscription_sync_task(monkeypatch):
    calls = []
    task = CrawlTask(id=22, job_id=1, task_type="subscription_sync_full", site="bilibili.com", payload={})
    runtime = _noop_runtime(
        dispatcher=SimpleNamespace(claim_next=lambda **kwargs: task),
        worker_id="worker-1",
        lease_seconds=60,
        retry_delay_seconds=30,
    )

    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.recover_expired_tasks",
        lambda now=None, retry_delay_seconds=30: [],
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.start_task",
        lambda task_id, worker_id, now=None: calls.append(("start", task_id, worker_id)) or task,
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.execute_subscription_sync_task",
        lambda current_task: calls.append(("sync", current_task.id, current_task.task_type)),
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.complete_task",
        lambda task_id, worker_id, now=None: calls.append(("complete", task_id, worker_id)) or task,
    )

    ran = runtime.run_once()

    assert ran is True
    assert calls == [
        ("start", 22, "worker-1"),
        ("sync", 22, "subscription_sync_full"),
        ("complete", 22, "worker-1"),
    ]


def test_run_once_retries_task_on_failure(monkeypatch):
    calls = []
    task = CrawlTask(id=3, job_id=1, task_type="video_extract", site="youtube.com", payload={})
    progress_calls = []
    runtime = _noop_runtime(
        dispatcher=SimpleNamespace(claim_next=lambda **kwargs: task),
        worker_id="worker-1",
        lease_seconds=60,
        retry_delay_seconds=45,
        subscription_task_progress=SimpleNamespace(
            record_retry_transition=lambda current_task, **kwargs: progress_calls.append((current_task.id, kwargs)),
        ),
    )

    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.recover_expired_tasks",
        lambda now=None, retry_delay_seconds=30: [],
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.start_task",
        lambda task_id, worker_id, now=None: calls.append(("start", task_id, worker_id)) or task,
    )

    def _raise(_task):
        raise RuntimeError("boom")

    monkeypatch.setattr("workers.scheduling.workers.tasks.execute_video_extract_task", _raise)
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.retry_task",
        lambda task_id, worker_id, error_message, error_type, now=None, delay_seconds=30: calls.append(
            ("retry", task_id, worker_id, error_type, delay_seconds),
        ) or task,
    )

    ran = runtime.run_once()

    assert ran is True
    assert calls == [
        ("start", 3, "worker-1"),
        ("retry", 3, "worker-1", "RuntimeError", 45),
    ]
    assert progress_calls == [(3, {"now": progress_calls[0][1]["now"], "error_message": "boom"})]


def test_run_once_returns_false_when_no_task_is_claimed(monkeypatch):
    runtime = _noop_runtime(
        dispatcher=SimpleNamespace(claim_next=lambda **kwargs: None),
        worker_id="worker-1",
    )

    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.recover_expired_tasks",
        lambda now=None, retry_delay_seconds=30: [],
    )

    assert runtime.run_once() is False


def test_recover_expired_tasks_records_domain_progress(monkeypatch):
    progress_calls = []
    recovered_task = CrawlTask(
        id=41,
        job_id=1,
        task_type="subscription_sync_incremental",
        site="youtube.com",
        status="retry_wait",
        last_error="lease_expired",
        payload={"sync_state_id": 2},
    )
    runtime = _noop_runtime(
        worker_id="worker-1",
        retry_delay_seconds=45,
        subscription_task_progress=SimpleNamespace(
            record_retry_transition=lambda current_task, **kwargs: progress_calls.append((current_task.id, kwargs)),
        ),
    )
    now = datetime(2026, 4, 2, 13, 0, 0)

    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.recover_expired_tasks",
        lambda **kwargs: [recovered_task],
    )

    recovered_count = runtime._recover_expired_tasks(now=now)

    assert recovered_count == 1
    assert progress_calls == [(41, {"now": now, "error_message": "lease_expired"})]


def test_run_loop_fills_multiple_slots_with_concurrent_tasks(monkeypatch):
    started = []
    release_event = threading.Event()
    execute_gate = threading.Barrier(2)
    tasks = [
        CrawlTask(id=11, job_id=1, task_type="video_extract", site="youtube.com", payload={}),
        CrawlTask(id=12, job_id=1, task_type="video_extract", site="bilibili.com", payload={}),
    ]
    dispatcher = SimpleNamespace(claim_next=lambda **kwargs: tasks.pop(0) if tasks else None)
    runtime = _noop_runtime(
        dispatcher=dispatcher,
        worker_id="worker-1",
        lease_seconds=60,
        retry_delay_seconds=30,
        poll_interval_seconds=0.01,
        max_concurrency=2,
    )

    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.recover_expired_tasks",
        lambda now=None, retry_delay_seconds=30: [],
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.start_task",
        lambda task_id, worker_id, now=None: started.append((task_id, worker_id)) or next(task for task in [*tasks, CrawlTask(id=task_id, job_id=1, task_type="video_extract", site="youtube.com", payload={})] if task.id == task_id),
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.complete_task",
        lambda task_id, worker_id, now=None: CrawlTask(id=task_id, job_id=1, task_type="video_extract", site="youtube.com", payload={}),
    )

    def _execute(current_task):
        execute_gate.wait(timeout=1)
        release_event.wait(timeout=1)

    monkeypatch.setattr("workers.scheduling.workers.tasks.execute_video_extract_task", _execute)

    stop_event = threading.Event()
    thread = threading.Thread(target=runtime.run_loop, args=(stop_event,))
    thread.start()

    deadline = time.time() + 1
    while len(started) < 2 and time.time() < deadline:
        time.sleep(0.01)

    release_event.set()
    stop_event.set()
    thread.join(timeout=1)

    assert sorted(started) == [(11, "worker-1"), (12, "worker-1")]


def test_run_loop_renews_lease_for_running_tasks(monkeypatch):
    renew_calls = []
    release_event = threading.Event()
    task = CrawlTask(id=21, job_id=1, task_type="video_extract", site="youtube.com", payload={})
    dispatcher = SimpleNamespace(claim_next=lambda **kwargs: task if not renew_calls else None)
    runtime = _noop_runtime(
        dispatcher=dispatcher,
        worker_id="worker-1",
        lease_seconds=1,
        retry_delay_seconds=30,
        poll_interval_seconds=0.01,
        max_concurrency=1,
    )

    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.recover_expired_tasks",
        lambda now=None, retry_delay_seconds=30: [],
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.start_task",
        lambda task_id, worker_id, now=None: task,
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.leases.crawl_task_service.renew_task_lease",
        lambda task_id, worker_id, now=None, lease_seconds=60: renew_calls.append((task_id, worker_id)),
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.complete_task",
        lambda task_id, worker_id, now=None: task,
    )

    def _execute(_task):
        release_event.wait(timeout=1)

    monkeypatch.setattr("workers.scheduling.workers.tasks.execute_video_extract_task", _execute)

    stop_event = threading.Event()
    thread = threading.Thread(target=runtime.run_loop, args=(stop_event,))
    thread.start()

    deadline = time.time() + 1
    while not renew_calls and time.time() < deadline:
        time.sleep(0.01)

    release_event.set()
    stop_event.set()
    thread.join(timeout=1)

    assert renew_calls
    assert all(call == (21, "worker-1") for call in renew_calls)


def test_renew_active_leases_ignores_lost_task_ownership(monkeypatch):
    runtime = _noop_runtime(worker_id="worker-1", lease_seconds=1)
    future = Future()
    runtime._lease_tracker.futures = {future}

    last_renewed_at = datetime(2026, 4, 2, 13, 0, 0)
    runtime._lease_tracker.active_leases[future] = ActiveTaskLease(task_id=99, last_renewed_at=last_renewed_at)

    monkeypatch.setattr(
        "workers.scheduling.workers.leases.crawl_task_service.renew_task_lease",
        lambda **kwargs: (_ for _ in ()).throw(CrawlTaskOwnershipError("lost ownership")),
    )

    runtime._lease_tracker.renew_active_leases(now=last_renewed_at + timedelta(seconds=1))

    assert future not in runtime._lease_tracker.active_leases


def test_run_task_does_not_retry_when_task_ownership_is_lost_on_complete(monkeypatch):
    task = CrawlTask(id=31, job_id=1, task_type="video_extract", site="youtube.com", payload={})
    runtime = _noop_runtime(worker_id="worker-1", retry_delay_seconds=45)
    retry_calls = []

    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.start_task",
        lambda task_id, worker_id, now=None: task,
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.execute_video_extract_task",
        lambda current_task: None,
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.complete_task",
        lambda task_id, worker_id, now=None: (_ for _ in ()).throw(CrawlTaskOwnershipError("lost ownership")),
    )
    monkeypatch.setattr(
        "workers.scheduling.workers.tasks.crawl_task_service.retry_task",
        lambda **kwargs: retry_calls.append(kwargs),
    )

    runtime.task_runner.run_task(task, claimed_at=datetime(2026, 4, 2, 13, 0, 0))

    assert retry_calls == []
