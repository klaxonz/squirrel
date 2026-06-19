import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domains.subscription.application.services.core.update.models import SubscriptionUpdateResult
from domains.subscription.interfaces.http import router
from domains.subscription.interfaces.http.dependencies import (
    get_subscription_crud_service,
    get_subscription_import_service,
    get_subscription_list_service,
    get_subscription_manage_service,
    get_subscription_scheduler,
)
from domains.user.application.services.auth import get_current_user


def _build_client(monkeypatch, overrides=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    for dependency, override in (overrides or {}).items():
        app.dependency_overrides[dependency] = override
    monkeypatch.setattr(
        'domains.subscription.interfaces.http.basic.SiteCatalog.is_site_enabled',
        classmethod(lambda cls, site=None, domain=None: True),
    )
    return TestClient(app)


def test_subscribe_route_creates_subscription_synchronously(monkeypatch):
    calls = []

    class FakeImportService:
        @staticmethod
        def handle_subscribe_request(url, user_id):
            calls.append((url, user_id))
            return SimpleNamespace(id=42)

    client = _build_client(
        monkeypatch,
        {get_subscription_import_service: lambda: FakeImportService()},
    )

    response = client.post(
        '/api/subscription/subscribe',
        json={
            'url': 'https://space.bilibili.com/32781024',
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['data'] == {
        'subscription_id': 42,
        'is_subscribed': True,
    }
    assert calls == [('https://space.bilibili.com/32781024', 7)]


def test_refresh_direct_runs_subscription_without_scheduler_queue(monkeypatch):
    calls = []

    class FakeCrudService:
        @staticmethod
        def verify_subscription_access(user_id, subscription_id):
            return SimpleNamespace(id=subscription_id, url='https://space.bilibili.com/32781024'), 'ok'

    class FakeScheduler:
        @staticmethod
        def run_one_inline(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                subscription_id=kwargs['subscription_id'],
                sync_state_id=12,
                status='success',
                request_id='direct:run-1',
                run_id='run-1',
                result=SubscriptionUpdateResult(
                    subscription_id=kwargs['subscription_id'],
                    success=True,
                    videos_found=3,
                    videos_enqueued=2,
                ),
            )

        @staticmethod
        def schedule_one(**kwargs):
            raise AssertionError('direct refresh should not schedule a task')

    client = _build_client(
        monkeypatch,
        {
            get_subscription_crud_service: lambda: FakeCrudService(),
            get_subscription_scheduler: lambda: FakeScheduler(),
        },
    )

    response = client.post('/api/subscription/42/refresh/direct?mode=full')

    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['data']['status'] == 'success'
    assert body['data']['videosFound'] == 3
    assert body['data']['videosExtracted'] == 2
    assert calls[0]['subscription_id'] == 42
    assert calls[0]['user_id'] == 7
    assert calls[0]['mode'].value == 'full'


def test_toggle_special_follow_route_updates_current_user_subscription(monkeypatch):
    calls = []

    class FakeManageService:
        @staticmethod
        def toggle_special_follow_status(user_id, subscription_id, is_special_followed):
            calls.append((user_id, subscription_id, is_special_followed))
            return True

    client = _build_client(
        monkeypatch,
        {get_subscription_manage_service: lambda: FakeManageService()},
    )

    response = client.post(
        '/api/subscription/toggle-special-follow',
        json={
            'subscription_id': 42,
            'is_enable': True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['data'] == {'success': True}
    assert calls == [(7, 42, True)]


def test_list_subscriptions_forwards_query_model_values(monkeypatch):
    captured = {}

    class FakeListService:
        @staticmethod
        def list_subscriptions(user_id, query, type, nsfw, page, page_size, domains, special):
            captured.update(
                {
                    'user_id': user_id,
                    'query': query,
                    'type': type,
                    'nsfw': nsfw,
                    'page': page,
                    'page_size': page_size,
                    'domains': domains,
                    'special': special,
                }
            )
            return [], 0

    monkeypatch.setattr(
        'domains.subscription.interfaces.http.basic.SiteCatalog.resolve_domains',
        classmethod(lambda cls, site: ['youtube.com'] if site == 'youtube' else []),
    )
    client = _build_client(
        monkeypatch,
        {get_subscription_list_service: lambda: FakeListService()},
    )

    response = client.get(
        '/api/subscription/list',
        params={
            'query': 'abc',
            'type': 'channel',
            'nsfw': 'yes',
            'special': 'no',
            'site': 'youtube',
            'page': 3,
            'pageSize': 25,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['data']['page'] == 3
    assert body['data']['pageSize'] == 25
    assert captured == {
        'user_id': 7,
        'query': 'abc',
        'type': 'channel',
        'nsfw': 'yes',
        'page': 3,
        'page_size': 25,
        'domains': ['youtube.com'],
        'special': 'no',
    }
