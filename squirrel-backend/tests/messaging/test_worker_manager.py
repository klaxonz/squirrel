import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from messaging import worker as worker_manager


class _FakeRunner:
    def __init__(self):
        self.started = False

    def start(self):
        self.started = True

    def threads(self):
        return [object(), object()]


def test_worker_start_runs_queue_runner_and_crawl_runtime(monkeypatch):
    calls = []
    fake_runner = _FakeRunner()

    monkeypatch.setattr(worker_manager, "crawl_worker_start", lambda: calls.append("crawl-start"))
    monkeypatch.setattr(worker_manager, "crawl_worker_status", lambda: {"running": True, "count": 1})
    monkeypatch.setattr(worker_manager, "WorkerRunner", lambda: fake_runner)
    monkeypatch.setattr(worker_manager, "_workers_running", False)
    monkeypatch.setattr(worker_manager, "_worker_threads", [])
    monkeypatch.setattr(worker_manager, "_runner", None)

    worker_manager.worker_start()

    assert calls == ["crawl-start"]
    assert fake_runner.started is True
    status = worker_manager.worker_status()
    assert status == {"running": True, "count": 3}


def test_worker_stop_stops_queue_runner_and_crawl_runtime(monkeypatch):
    calls = []

    monkeypatch.setattr(worker_manager, "crawl_worker_stop", lambda: calls.append("crawl-stop"))
    monkeypatch.setattr(worker_manager, "_workers_running", True)
    monkeypatch.setattr(worker_manager, "_worker_threads", [object()])

    worker_manager.worker_stop()

    assert calls == ["crawl-stop"]
    assert worker_manager.worker_status() == {"running": False, "count": 0}
