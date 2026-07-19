from domains.rss.application.services.account.remote_status import RssRemoteStatusSyncer


class _ManualExecutor:
    def __init__(self) -> None:
        self.jobs = []

    def submit(self, function, *args):
        self.jobs.append((function, args))

    def run_next(self) -> None:
        function, args = self.jobs.pop(0)
        function(*args)


def test_remote_status_coalesces_not_yet_started_updates_to_latest_values(monkeypatch):
    executor = _ManualExecutor()
    syncer = RssRemoteStatusSyncer(executor=executor)
    calls = []

    class _Client:
        def update_entry(self, external_entry_id, *, is_read=None, is_starred=None):
            calls.append((external_entry_id, is_read, is_starred))

    monkeypatch.setattr(
        'domains.rss.application.services.account.remote_status.create_client',
        lambda config: _Client(),
    )

    syncer.update_entry_async(7, object(), 'entry-1', is_read=True)
    syncer.update_entry_async(7, object(), 'entry-1', is_read=False, is_starred=True)

    assert len(executor.jobs) == 1
    executor.run_next()

    assert calls == [('entry-1', False, True)]
    assert executor.jobs == []


def test_remote_status_serializes_update_that_arrives_while_same_entry_is_running(monkeypatch):
    executor = _ManualExecutor()
    syncer = RssRemoteStatusSyncer(executor=executor)
    config = object()
    calls = []
    active_calls = 0
    max_active_calls = 0

    class _Client:
        def update_entry(self, external_entry_id, *, is_read=None, is_starred=None):
            nonlocal active_calls, max_active_calls
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
            calls.append((external_entry_id, is_read, is_starred))
            if len(calls) == 1:
                syncer.update_entry_async(7, config, external_entry_id, is_read=False)
            active_calls -= 1

    monkeypatch.setattr(
        'domains.rss.application.services.account.remote_status.create_client',
        lambda current_config: _Client(),
    )

    syncer.update_entry_async(7, config, 'entry-1', is_read=True)
    executor.run_next()

    assert calls == [
        ('entry-1', True, None),
        ('entry-1', False, None),
    ]
    assert max_active_calls == 1
    assert executor.jobs == []
