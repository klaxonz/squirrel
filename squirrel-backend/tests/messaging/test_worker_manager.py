import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from workers.messaging import worker as worker_manager


def test_worker_start_runs_crawl_runtime(monkeypatch):
    calls = []

    monkeypatch.setattr(worker_manager, 'crawl_worker_start', lambda: calls.append('crawl-start'))
    monkeypatch.setattr(worker_manager, 'crawl_worker_status', lambda: {'running': True, 'count': 2})
    monkeypatch.setattr(worker_manager, '_workers_running', False)

    worker_manager.worker_start()

    assert calls == ['crawl-start']
    status = worker_manager.worker_status()
    assert status == {'running': True, 'count': 2}


def test_worker_stop_stops_crawl_runtime(monkeypatch):
    calls = []

    monkeypatch.setattr(worker_manager, 'crawl_worker_stop', lambda: calls.append('crawl-stop'))
    monkeypatch.setattr(worker_manager, '_workers_running', True)
    monkeypatch.setattr(worker_manager, 'crawl_worker_status', lambda: {'running': False, 'count': 0})

    worker_manager.worker_stop()

    assert calls == ['crawl-stop']
    assert worker_manager.worker_status() == {'running': False, 'count': 0}
