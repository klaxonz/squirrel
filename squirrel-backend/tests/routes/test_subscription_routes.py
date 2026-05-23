from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.subscription import router
from utils.jwt_helper import get_current_user


def _build_client(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    monkeypatch.setattr(
        'routes.subscription.SiteCatalog.is_site_enabled',
        classmethod(lambda cls, site=None, domain=None: True),
    )
    return TestClient(app)


def test_subscribe_route_creates_subscription_synchronously(monkeypatch):
    calls = []

    def _handle_subscribe_request(url, user_id):
        calls.append((url, user_id))
        return SimpleNamespace(id=42)

    def _enqueue_message(_url, _user_id):
        raise AssertionError('manual subscribe should not enqueue a message')

    monkeypatch.setattr(
        'routes.subscription.subscription_service.handle_subscribe_request',
        _handle_subscribe_request,
    )
    monkeypatch.setattr(
        'routes.subscription.subscription_service.create_subscribe_message',
        _enqueue_message,
    )
    client = _build_client(monkeypatch)

    response = client.post('/api/subscription/subscribe', json={
        'url': 'https://space.bilibili.com/32781024',
    })

    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['data'] == {
        'subscription_id': 42,
        'is_subscribed': True,
    }
    assert calls == [('https://space.bilibili.com/32781024', 7)]
