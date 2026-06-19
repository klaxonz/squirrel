from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.rss.interfaces.http.dependencies import get_rss_service
from domains.rss.interfaces.http.sync import router
from domains.user.application.services.auth import get_current_user


class FakeThread:
    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


class FakeRssService:
    def __init__(self):
        self.calls = []

    def get_sync_progress(self, user_id, account_id):
        self.calls.append({'method': 'get_sync_progress', 'user_id': user_id, 'account_id': account_id})
        return {'running': False}

    def sync_account(self, user_id, account_id, *, entry_limit=None, force_full_sync=False):
        self.calls.append(
            {
                'method': 'sync_account',
                'user_id': user_id,
                'account_id': account_id,
                'entry_limit': entry_limit,
                'force_full_sync': force_full_sync,
            }
        )


def test_start_rss_sync_forwards_query_model_values(monkeypatch):
    fake_service = FakeRssService()
    monkeypatch.setattr('domains.rss.interfaces.http.sync.Thread', FakeThread)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_rss_service] = lambda: fake_service
    client = TestClient(app)

    route_response = client.post(
        '/accounts/11/sync/start',
        params={
            'entryLimit': 25,
            'forceFullSync': 'true',
        },
    )

    assert route_response.status_code == 200
    assert route_response.json()['data'] == {'started': True, 'account_id': 11}
    assert fake_service.calls == [
        {'method': 'get_sync_progress', 'user_id': 7, 'account_id': 11},
        {
            'method': 'sync_account',
            'user_id': 7,
            'account_id': 11,
            'entry_limit': 25,
            'force_full_sync': True,
        },
    ]
