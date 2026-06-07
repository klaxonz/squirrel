import sys
from pathlib import Path
from threading import Event

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from processes.managers import scheduler_manager


class _FakeScheduler:
    def __init__(self):
        self.jobs = []
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class _FakeThread:
    def __init__(self, target=None, args=None, daemon=None):
        self.target = target
        self.args = args or ()
        self.daemon = daemon
        self.started = False
        self.joined = False

    def start(self):
        self.started = True

    def join(self, timeout=None):
        self.joined = True


def test_scheduler_start_and_stop_manage_outbox_listener_thread(monkeypatch):
    started = []
    stop_event_holder = {}

    monkeypatch.setattr(scheduler_manager, "Scheduler", _FakeScheduler)
    monkeypatch.setattr(scheduler_manager.dynamic_task_manager, "initialize", lambda scheduler: None)
    monkeypatch.setattr(scheduler_manager, "ensure_system_tasks", lambda: None)
    monkeypatch.setattr(scheduler_manager, "_seed_task_fingerprints", lambda: None)
    monkeypatch.setattr(scheduler_manager.dynamic_task_manager, "load_and_register_tasks", lambda: None)
    monkeypatch.setattr(scheduler_manager, "_update_scheduler_status", lambda **kwargs: None)
    monkeypatch.setattr(scheduler_manager, "_sync_scheduled_tasks", lambda: None)
    monkeypatch.setattr(scheduler_manager, "_consume_manual_triggers", lambda: None)

    def _fake_thread_factory(target=None, args=None, daemon=None):
        thread = _FakeThread(target=target, args=args, daemon=daemon)
        started.append(thread)
        return thread

    def _fake_create_stop_event():
        event = Event()
        stop_event_holder["event"] = event
        return event

    monkeypatch.setattr(scheduler_manager, "Thread", _fake_thread_factory)
    monkeypatch.setattr(scheduler_manager.outbox_event_service, "create_listener_stop_event", _fake_create_stop_event)
    monkeypatch.setattr(scheduler_manager.outbox_event_service, "run_notification_listener", lambda event: None)

    scheduler_manager.scheduler_start()

    assert len(started) == 2
    assert scheduler_manager._outbox_listener_thread is started[1]
    assert scheduler_manager._outbox_listener_thread.started is True
    assert stop_event_holder["event"].is_set() is False

    scheduler_manager.scheduler_stop()

    assert stop_event_holder["event"].is_set() is True
    assert started[1].joined is True
