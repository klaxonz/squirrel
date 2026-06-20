import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domains.subscription.interfaces.http import router
from domains.subscription.interfaces.http.dependencies import get_subscription_import_service
from domains.user.application.services.auth import get_current_user
from tests.common.app_factory import create_test_app


def _build_client(monkeypatch, import_service=None):
    app = create_test_app()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type('User', (), {'id': 7})()
    if import_service:
        app.dependency_overrides[get_subscription_import_service] = lambda: import_service
    else:
        app.dependency_overrides[get_subscription_import_service] = lambda: type(
            'ImportService',
            (),
            {'get_plugin_supported_sites': staticmethod(lambda _cap: ['javdb'])},
        )()
    # All supported sites are enabled — avoids depending on the runtime provider
    # snapshot being populated by the autouse fixture.
    monkeypatch.setattr(
        'domains.subscription.interfaces.http.site_imports.SiteCatalog.get_enabled_site_names',
        classmethod(lambda cls: {'javdb'}),
    )
    return TestClient(app)


def test_preview_import_route_forwards_cursor_and_limit(monkeypatch):
    captured = {}

    class FakeImportService:
        @staticmethod
        def get_plugin_supported_sites(_cap):
            return ['javdb']

        @staticmethod
        def preview_user_subscriptions(site_name, user_id, *, cursor_payload=None, limit=None):
            captured.update(
                {
                    'site_name': site_name,
                    'user_id': user_id,
                    'cursor_payload': cursor_payload,
                    'limit': limit,
                }
            )
            return {
                'site': site_name,
                'total': 1000,
                'loaded': 50,
                'imported': 0,
                'not_imported': 50,
                'subscriptions': [],
                'has_more': True,
                'cursor_payload': {'page': 3},
                'stop_reason': 'batch_exhausted',
            }

    client = _build_client(monkeypatch, FakeImportService())

    response = client.get(
        '/api/subscription/import/javdb/preview',
        params={'cursor': '{"page":2}', 'limit': 50},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body['code'] == 0
    assert body['data']['has_more'] is True
    assert body['data']['cursor_payload'] == {'page': 3}
    assert captured == {
        'site_name': 'javdb',
        'user_id': 7,
        'cursor_payload': {'page': 2},
        'limit': 50,
    }


def test_preview_import_route_rejects_invalid_cursor_json(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get(
        '/api/subscription/import/javdb/preview',
        params={'cursor': '{not-json}', 'limit': 50},
    )

    assert response.status_code == 400
    body = response.json()
    assert body['code'] == 400
    assert '无效的预览游标' in body['msg']


def test_preview_import_route_rejects_non_object_cursor(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get(
        '/api/subscription/import/javdb/preview',
        params={'cursor': '[]', 'limit': 50},
    )

    assert response.status_code == 400
    body = response.json()
    assert body['code'] == 400
    assert body['msg'] == '无效的预览游标: 必须为 JSON object'


def test_get_import_sites_filters_disabled_sites_in_original_order(monkeypatch):
    calls = {'count': 0}

    def _get_enabled_site_names():
        calls['count'] += 1
        return {'javdb', 'bilibili'}

    class FakeImportService:
        @staticmethod
        def get_plugin_supported_sites(_cap):
            return [' JAVDB ', 'youtube', 'javdb', 'bilibili']

    client = _build_client(monkeypatch, FakeImportService())
    monkeypatch.setattr(
        'domains.subscription.interfaces.http.site_imports.SiteCatalog.get_enabled_site_names',
        classmethod(lambda cls: _get_enabled_site_names()),
    )

    response = client.get('/api/subscription/import/sites')

    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['data']['sites'] == ['javdb', 'bilibili']
    assert calls['count'] == 1
