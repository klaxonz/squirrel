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

    monkeypatch.setattr(crawl_worker_manager.settings.crawl, "slots_per_process", 3, raising=False)
    monkeypatch.setattr(
        crawl_worker_manager,
        "CrawlWorkerRuntime",
        lambda **kwargs: runtimes.append(_FakeRuntime(**kwargs)) or runtimes[-1],
    )
    monkeypatch.setattr(
        crawl_worker_manager.threading,
        "Thread",
        lambda **kwargs: threads.append(_FakeThread(**kwargs)) or threads[-1],
    )
    monkeypatch.setattr(crawl_worker_manager, "_workers_running", False)
    monkeypatch.setattr(crawl_worker_manager, "_worker_threads", [])
    monkeypatch.setattr(crawl_worker_manager, "_stop_event", None)

    crawl_worker_manager.crawl_worker_start()

    assert [runtime.kwargs["worker_id"] for runtime in runtimes] == ["crawl-runtime-1"]
    assert runtimes[0].kwargs["max_concurrency"] == 3
    assert [thread.name for thread in threads] == ["crawl-runtime-1"]
    assert all(thread.started for thread in threads)
    assert crawl_worker_manager.crawl_worker_status() == {"running": True, "count": 1}
