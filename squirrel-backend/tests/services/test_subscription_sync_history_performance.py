import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services import subscription_sync_history_service


@contextmanager
def _managed_session(session):
    yield session


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def scalars(self):
        return self


def test_list_runs_uses_count_helper_instead_of_loading_all_rows(monkeypatch):
    run = SimpleNamespace(
        run_id="run-1",
        site="youtube.com",
        sync_mode="incremental",
        trigger="manual",
        status="success",
        current_phase="completed",
        request_id="req-1",
        trace_id="trace-1",
        queued_at=None,
        started_at=None,
        finished_at=None,
        duration_ms=0,
        failure_count=0,
        error_type=None,
        error_message=None,
        videos_found=3,
        videos_enqueued=2,
        videos_extracted=2,
        videos_skipped=1,
        pending_video_count=0,
        last_event_at=None,
    )
    subscription = SimpleNamespace(
        id=1,
        name="Demo",
        avatar=None,
    )

    session = SimpleNamespace()
    executed_queries = []

    def _execute(query):
        executed_queries.append(query)
        return _Result([(run, subscription)])

    session.execute = _execute

    count_queries = []

    monkeypatch.setattr(subscription_sync_history_service, "get_session", lambda: _managed_session(session))
    monkeypatch.setattr(subscription_sync_history_service, "_resolve_site_icon_url", lambda site: None)
    monkeypatch.setattr(
        subscription_sync_history_service,
        "_count_query_rows",
        lambda current_session, query: count_queries.append((current_session, query)) or 7,
    )

    result = subscription_sync_history_service.list_runs(user_id=1, page=1, page_size=20)

    assert result["total"] == 7
    assert len(result["data"]) == 1
    assert len(executed_queries) == 1
    assert len(count_queries) == 1
    assert count_queries[0][0] is session


def test_list_run_events_checks_access_without_calling_get_run_detail(monkeypatch):
    event = SimpleNamespace(
        id=1,
        stream_id="run-1",
        subscription_id=1,
        sync_state_id=10,
        site="youtube.com",
        sync_mode="incremental",
        trigger="manual",
        request_id="req-1",
        trace_id="trace-1",
        event_type="completed",
        event_phase="completed",
        event_status="success",
        seq_no=3,
        message="done",
        payload={"videos_extracted": 2},
        occurred_at=None,
        projected_at=None,
    )

    session = SimpleNamespace()
    session.execute = lambda query: _Result([event])

    monkeypatch.setattr(subscription_sync_history_service, "get_session", lambda: _managed_session(session))
    monkeypatch.setattr(
        subscription_sync_history_service,
        "_run_exists_for_user",
        lambda current_session, run_id, user_id: True,
    )
    monkeypatch.setattr(
        subscription_sync_history_service,
        "get_run_detail",
        lambda run_id, user_id: (_ for _ in ()).throw(AssertionError("get_run_detail should not be used here")),
    )

    result = subscription_sync_history_service.list_run_events("run-1", 1)

    assert len(result) == 1
    assert result[0]["stream_id"] == "run-1"
