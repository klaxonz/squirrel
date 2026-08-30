import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from workers.scheduling.executors import manager as crawl_worker_manager


class _FakeRuntime:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def run_loop(self, _stop_event):
        return None


class _FakeThread:
    def __init__(self, *, target, args, daemon, name):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.name = name
        self.started = False

    def start(self):
        self.started = True


def test_crawl_worker_start_uses_configured_worker_count(monkeypatch):
    runtimes = []
    threads = []

    monkeypatch.setattr(crawl_worker_manager.settings.crawl, 'slots_per_process', 3, raising=False)
    monkeypatch.setattr(
        crawl_worker_manager,
        'CrawlWorkerRuntime',
        lambda **kwargs: runtimes.append(_FakeRuntime(**kwargs)) or runtimes[-1],
    )
    monkeypatch.setattr(
        crawl_worker_manager.threading,
        'Thread',
        lambda **kwargs: threads.append(_FakeThread(**kwargs)) or threads[-1],
    )
    monkeypatch.setattr(crawl_worker_manager, '_workers_running', False)
    monkeypatch.setattr(crawl_worker_manager, '_worker_threads', [])
    monkeypatch.setattr(crawl_worker_manager, '_stop_event', None)

    crawl_worker_manager.crawl_worker_start()

    worker_ids = [runtime.kwargs['worker_id'] for runtime in runtimes]
    assert len(worker_ids) == 1
    assert worker_ids[0].count(':') == 2
    assert runtimes[0].kwargs['max_concurrency'] == 3
    assert [thread.name for thread in threads] == ['crawl-runtime-1']
    assert all(thread.started for thread in threads)
    assert crawl_worker_manager.crawl_worker_status() == {'running': True, 'count': 1}


def test_create_runtime_injects_import_executor_from_composition_root(monkeypatch):
    captured = {}

    class _Services:
        lifecycle = object()
        orchestrator = object()
        crud = object()
        import_service = object()
        video_service = type('VideoService', (), {'extraction': object()})()

        def close(self):
            pass

    class _Runtime:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(crawl_worker_manager, 'SubscriptionService', _Services)
    monkeypatch.setattr(crawl_worker_manager, 'CrawlWorkerRuntime', _Runtime)

    runtime, services = crawl_worker_manager._create_runtime(worker_id='worker-1')

    assert runtime is not None
    assert services is not None
    assert captured['subscription_import_executor']._import_service is services.import_service


def test_run_runtime_closes_composed_services_after_runtime_exit():
    calls = []

    class _Runtime:
        def run_loop(self, stop_event):
            calls.append(('run', stop_event))

    class _Services:
        def close(self):
            calls.append(('close',))

    stop_event = object()
    crawl_worker_manager._run_runtime(_Runtime(), _Services(), stop_event)

    assert [call[0] for call in calls] == ['run', 'close']
