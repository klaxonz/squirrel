from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeResponse
from services import site_login_status_service


def test_get_supported_sites_reads_login_status_registrations(monkeypatch):
    registrations = [
        SimpleNamespace(capability='check_login_status', site_name='youtube'),
        SimpleNamespace(capability='extract_video', site_name='youtube'),
        SimpleNamespace(capability='check_login_status', site_name='bilibili'),
        SimpleNamespace(capability='check_login_status', site_name='youtube'),
        SimpleNamespace(capability='check_login_status', site_name=''),
    ]

    monkeypatch.setattr(
        site_login_status_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(
            get_snapshot=lambda: SimpleNamespace(registrations=registrations),
        ),
    )

    assert site_login_status_service.get_supported_sites() == {'youtube', 'bilibili'}


def test_test_site_login_status_returns_fallback_when_route_missing(monkeypatch):
    class _FakeGateway:
        def resolve_route(self, capability, site_name=None, domain=None):
            return None

    monkeypatch.setattr(
        site_login_status_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    payload = site_login_status_service.test_site_login_status('youtube')

    assert payload['site_name'] == 'youtube'
    assert payload['supported'] is False
    assert payload['logged_in'] is False
    assert payload['message'] == '该站点未提供登录检测实现'
    assert payload['checked_at']


def test_test_site_login_status_normalizes_runtime_payload(monkeypatch):
    calls = []

    class _FakeGateway:
        def resolve_route(self, capability, site_name=None, domain=None):
            return object()

        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            calls.append({
                'capability': capability,
                'payload': payload,
                'site_name': site_name,
                'domain': domain,
                'timeout_ms': timeout_ms,
            })
            return PluginInvokeResponse(
                request_id='login-1',
                ok=True,
                data={
                    'logged_in': True,
                    'message': 'ok',
                    'extra': {'account': 'demo'},
                },
            )

    monkeypatch.setattr(
        site_login_status_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    payload = site_login_status_service.test_site_login_status('youtube')

    assert calls == [{
        'capability': 'check_login_status',
        'payload': None,
        'site_name': 'youtube',
        'domain': None,
        'timeout_ms': None,
    }]
    assert payload['site_name'] == 'youtube'
    assert payload['supported'] is True
    assert payload['logged_in'] is True
    assert payload['message'] == 'ok'
    assert payload['extra'] == {'account': 'demo'}
    assert payload['checked_at']
