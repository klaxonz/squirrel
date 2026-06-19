from infrastructure.scheduling import lifecycle as scheduler_manager


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


def test_scheduler_start_and_stop_manage_heartbeat_thread(monkeypatch):
    started = []

    monkeypatch.setattr(scheduler_manager, 'Scheduler', _FakeScheduler)
    monkeypatch.setattr(scheduler_manager.dynamic_task_manager, 'initialize', lambda scheduler: None)
    monkeypatch.setattr(scheduler_manager, 'ensure_system_tasks', lambda: None)
    monkeypatch.setattr(scheduler_manager._task_synchronizer, 'seed_task_fingerprints', lambda: None)
    monkeypatch.setattr(scheduler_manager.dynamic_task_manager, 'load_and_register_tasks', lambda: None)
    monkeypatch.setattr(scheduler_manager, '_update_scheduler_status', lambda **kwargs: None)
    monkeypatch.setattr(scheduler_manager._task_synchronizer, 'sync_scheduled_tasks', lambda: None)
    monkeypatch.setattr(scheduler_manager._task_synchronizer, 'consume_manual_triggers', lambda: None)

    def _fake_thread_factory(target=None, args=None, daemon=None):
        thread = _FakeThread(target=target, args=args, daemon=daemon)
        started.append(thread)
        return thread

    monkeypatch.setattr(scheduler_manager, 'Thread', _fake_thread_factory)

    scheduler_manager.scheduler_start()

    assert len(started) == 1
    assert scheduler_manager._heartbeat_thread is started[0]
    assert scheduler_manager._heartbeat_thread.started is True

    scheduler_manager.scheduler_stop()

    assert started[0].joined is True
