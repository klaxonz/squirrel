from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.subscription import router
from services.subscription_update.models import SubscriptionUpdateResult
from utils.jwt_helper import get_current_user
import services.subscription_update as subscription_update


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


def test_refresh_direct_runs_subscription_without_scheduler_queue(monkeypatch):
    calls = []

    monkeypatch.setattr(
        'routes.subscription.subscription_service.verify_subscription_access',
        lambda user_id, subscription_id: (
            SimpleNamespace(id=subscription_id, url='https://space.bilibili.com/32781024'),
            'ok',
        ),
    )

    def _run_one_inline(**kwargs):
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

    monkeypatch.setattr(subscription_update.scheduler, 'run_one_inline', _run_one_inline)
    monkeypatch.setattr(
        subscription_update.scheduler,
        'schedule_one',
        lambda **kwargs: (_ for _ in ()).throw(AssertionError('direct refresh should not schedule a task')),
    )
    client = _build_client(monkeypatch)

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
