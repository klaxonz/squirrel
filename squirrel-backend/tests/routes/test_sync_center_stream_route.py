from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.subscription import router
from utils.jwt_helper import get_current_user


def test_sync_center_stream_emits_initial_snapshots(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)

    async def _fake_stream(*, user_id, selected_run_id):
        yield 'event: feed_snapshot\ndata: {"overview":{"running_count":1}}\n\n'
        yield 'event: extract_snapshot\ndata: {"overview":{"running_count":2}}\n\n'
        yield 'event: run_detail\ndata: {"run":{"run_id":"run-7"},"events":[]}\n\n'

    monkeypatch.setattr('routes.subscription.sync_center_stream_service.stream_sync_center_events', _fake_stream)

    client = TestClient(app)
    with client.stream('GET', '/api/subscription/sync-center/stream', params={'selectedRunId': 'run-7'}) as response:
        body = ''.join(response.iter_text())

    assert response.status_code == 200
    assert 'event: feed_snapshot' in body
    assert 'event: extract_snapshot' in body
    assert 'event: run_detail' in body
