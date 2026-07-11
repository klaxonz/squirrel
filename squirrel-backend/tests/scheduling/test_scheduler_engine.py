from infrastructure.scheduling import engine as scheduler_engine


class _FakeThread:
    def __init__(self, target=None, args=None, daemon=None, name=None):
        self.target = target
        self.args = args or ()
        self.daemon = daemon
        self.name = name
        self.started = False
        self.joined = False
        self.join_timeout = None
        self._alive = False

    def start(self):
        self.started = True
        self._alive = True

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        self.joined = True
        self.join_timeout = timeout
        self._alive = False


def _patch_thread_factory(monkeypatch):
    threads = []

    def _fake_thread_factory(target=None, args=None, daemon=None, name=None):
        thread = _FakeThread(target=target, args=args, daemon=daemon, name=name)
        threads.append(thread)
        return thread

    monkeypatch.setattr(scheduler_engine, 'Thread', _fake_thread_factory)
    return threads


def test_scheduler_start_launches_run_loop_on_fresh_instance(monkeypatch):
    threads = _patch_thread_factory(monkeypatch)
    registered = []
    monkeypatch.setattr(scheduler_engine.thread_manager, 'register', lambda thread: registered.append(thread))

    scheduler = scheduler_engine.Scheduler()

    scheduler.start()

    assert len(threads) == 1
    assert threads[0].name == 'scheduler-run-loop'
    assert threads[0].daemon is True
    assert threads[0].started is True
    assert registered == [threads[0]]
    assert scheduler.running is True


def test_scheduler_start_is_idempotent_while_run_loop_is_alive(monkeypatch):
    threads = _patch_thread_factory(monkeypatch)
    monkeypatch.setattr(scheduler_engine.thread_manager, 'register', lambda thread: None)

    scheduler = scheduler_engine.Scheduler()

    scheduler.start()
    scheduler.start()

    assert len(threads) == 1


def test_scheduler_stop_signals_and_joins_run_loop(monkeypatch):
    threads = _patch_thread_factory(monkeypatch)
    monkeypatch.setattr(scheduler_engine.thread_manager, 'register', lambda thread: None)

    scheduler = scheduler_engine.Scheduler()
    scheduler.start()

    scheduler.stop()

    assert scheduler.running is False
    assert threads[0].joined is True
    assert threads[0].join_timeout == scheduler_engine._POLL_INTERVAL_SECONDS + 1
