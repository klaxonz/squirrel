from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.crawl_task import CrawlTask
from processes.managers.crawl_worker_runtime import CrawlWorkerRuntime


def test_run_once_executes_video_extract_task(monkeypatch):
    calls = []
    task = CrawlTask(id=1, job_id=1, task_type='video_extract', site='youtube.com', payload={})
    runtime = CrawlWorkerRuntime(
        dispatcher=SimpleNamespace(claim_next=lambda **kwargs: task),
        worker_id='worker-1',
        lease_seconds=60,
        retry_delay_seconds=30,
    )

    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.recover_expired_tasks',
        lambda now=None, retry_delay_seconds=30: 0,
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.start_task',
        lambda task_id, worker_id, now=None: calls.append(('start', task_id, worker_id)),
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.execute_video_extract_task',
        lambda current_task: calls.append(('video', current_task.id)),
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.complete_task',
        lambda task_id, worker_id, now=None: calls.append(('complete', task_id, worker_id)),
    )

    ran = runtime.run_once()

    assert ran is True
    assert calls == [
        ('start', 1, 'worker-1'),
        ('video', 1),
        ('complete', 1, 'worker-1'),
    ]


def test_run_once_executes_subscription_sync_task(monkeypatch):
    calls = []
    task = CrawlTask(id=2, job_id=1, task_type='subscription_sync', site='bilibili.com', payload={})
    runtime = CrawlWorkerRuntime(
        dispatcher=SimpleNamespace(claim_next=lambda **kwargs: task),
        worker_id='worker-1',
        lease_seconds=60,
        retry_delay_seconds=30,
    )

    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.recover_expired_tasks',
        lambda now=None, retry_delay_seconds=30: 0,
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.start_task',
        lambda task_id, worker_id, now=None: calls.append(('start', task_id, worker_id)),
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.execute_subscription_sync_task',
        lambda current_task: calls.append(('sync', current_task.id)),
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.complete_task',
        lambda task_id, worker_id, now=None: calls.append(('complete', task_id, worker_id)),
    )

    ran = runtime.run_once()

    assert ran is True
    assert calls == [
        ('start', 2, 'worker-1'),
        ('sync', 2),
        ('complete', 2, 'worker-1'),
    ]


def test_run_once_retries_task_on_failure(monkeypatch):
    calls = []
    task = CrawlTask(id=3, job_id=1, task_type='video_extract', site='youtube.com', payload={})
    runtime = CrawlWorkerRuntime(
        dispatcher=SimpleNamespace(claim_next=lambda **kwargs: task),
        worker_id='worker-1',
        lease_seconds=60,
        retry_delay_seconds=45,
    )

    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.recover_expired_tasks',
        lambda now=None, retry_delay_seconds=30: 0,
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.start_task',
        lambda task_id, worker_id, now=None: calls.append(('start', task_id, worker_id)),
    )

    def _raise(_task):
        raise RuntimeError('boom')

    monkeypatch.setattr('processes.managers.crawl_worker_runtime.execute_video_extract_task', _raise)
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.retry_task',
        lambda task_id, worker_id, error_message, error_type, now=None, delay_seconds=30: calls.append(
            ('retry', task_id, worker_id, error_type, delay_seconds)
        ),
    )

    ran = runtime.run_once()

    assert ran is True
    assert calls == [
        ('start', 3, 'worker-1'),
        ('retry', 3, 'worker-1', 'RuntimeError', 45),
    ]


def test_run_once_returns_false_when_no_task_is_claimed(monkeypatch):
    runtime = CrawlWorkerRuntime(
        dispatcher=SimpleNamespace(claim_next=lambda **kwargs: None),
        worker_id='worker-1',
    )

    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.recover_expired_tasks',
        lambda now=None, retry_delay_seconds=30: 0,
    )

    assert runtime.run_once() is False


def test_run_loop_fills_multiple_slots_with_concurrent_tasks(monkeypatch):
    started = []
    release_event = threading.Event()
    execute_gate = threading.Barrier(2)
    tasks = [
        CrawlTask(id=11, job_id=1, task_type='video_extract', site='youtube.com', payload={}),
        CrawlTask(id=12, job_id=1, task_type='video_extract', site='bilibili.com', payload={}),
    ]
    dispatcher = SimpleNamespace(claim_next=lambda **kwargs: tasks.pop(0) if tasks else None)
    runtime = CrawlWorkerRuntime(
        dispatcher=dispatcher,
        worker_id='worker-1',
        lease_seconds=60,
        retry_delay_seconds=30,
        poll_interval_seconds=0.01,
        max_concurrency=2,
    )

    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.recover_expired_tasks',
        lambda now=None, retry_delay_seconds=30: 0,
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.start_task',
        lambda task_id, worker_id, now=None: started.append((task_id, worker_id)),
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.complete_task',
        lambda task_id, worker_id, now=None: None,
    )

    def _execute(current_task):
        execute_gate.wait(timeout=1)
        release_event.wait(timeout=1)

    monkeypatch.setattr('processes.managers.crawl_worker_runtime.execute_video_extract_task', _execute)

    stop_event = threading.Event()
    thread = threading.Thread(target=runtime.run_loop, args=(stop_event,))
    thread.start()

    deadline = time.time() + 1
    while len(started) < 2 and time.time() < deadline:
        time.sleep(0.01)

    release_event.set()
    stop_event.set()
    thread.join(timeout=1)

    assert sorted(started) == [(11, 'worker-1'), (12, 'worker-1')]


def test_run_loop_renews_lease_for_running_tasks(monkeypatch):
    renew_calls = []
    release_event = threading.Event()
    task = CrawlTask(id=21, job_id=1, task_type='video_extract', site='youtube.com', payload={})
    dispatcher = SimpleNamespace(claim_next=lambda **kwargs: task if not renew_calls else None)
    runtime = CrawlWorkerRuntime(
        dispatcher=dispatcher,
        worker_id='worker-1',
        lease_seconds=1,
        retry_delay_seconds=30,
        poll_interval_seconds=0.01,
        max_concurrency=1,
    )

    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.recover_expired_tasks',
        lambda now=None, retry_delay_seconds=30: 0,
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.start_task',
        lambda task_id, worker_id, now=None: None,
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.renew_task_lease',
        lambda task_id, worker_id, now=None, lease_seconds=60: renew_calls.append((task_id, worker_id)),
    )
    monkeypatch.setattr(
        'processes.managers.crawl_worker_runtime.crawl_task_service.complete_task',
        lambda task_id, worker_id, now=None: None,
    )

    def _execute(_task):
        release_event.wait(timeout=1)

    monkeypatch.setattr('processes.managers.crawl_worker_runtime.execute_video_extract_task', _execute)

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
    assert all(call == (21, 'worker-1') for call in renew_calls)
