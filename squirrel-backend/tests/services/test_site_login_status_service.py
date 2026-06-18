from types import SimpleNamespace

from crawl import SiteRuntimeInvokeResponse

from infrastructure.site_catalog.login_status import SiteLoginStatusService


def _make_manager(*, gateway=None, snapshot=None):
    """Build a minimal fake manager exposing the attributes the service reads."""
    return SimpleNamespace(gateway=gateway, get_snapshot=lambda: snapshot)


def test_get_supported_sites_reads_login_status_registrations():
    registrations = [
        SimpleNamespace(capability='check_login_status', site_name='youtube'),
        SimpleNamespace(capability='extract_video', site_name='youtube'),
        SimpleNamespace(capability='check_login_status', site_name='bilibili'),
        SimpleNamespace(capability='check_login_status', site_name='youtube'),
        SimpleNamespace(capability='check_login_status', site_name=''),
    ]
    manager = _make_manager(snapshot=SimpleNamespace(registrations=registrations))
    svc = SiteLoginStatusService(manager)

    result = svc.get_supported_sites()

    assert result == {'youtube', 'bilibili'}


def test_test_site_login_status_returns_fallback_when_route_missing():
    class _FakeGateway:
        def resolve_route(self, capability, site_name=None, domain=None):
            return None

    manager = _make_manager(gateway=_FakeGateway())
    svc = SiteLoginStatusService(manager)
    payload = svc.test_site_login_status('youtube')

    assert payload['site_name'] == 'youtube'
    assert payload['supported'] is False
    assert payload['logged_in'] is False
    assert payload['message'] == 'login check not supported for this site'
    assert payload['checked_at']


def test_test_site_login_status_normalizes_runtime_payload():
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
            return SiteRuntimeInvokeResponse(
                request_id='login-1',
                ok=True,
                data={
                    'logged_in': True,
                    'message': 'ok',
                    'extra': {'account': 'demo'},
                },
            )

    manager = _make_manager(gateway=_FakeGateway())
    svc = SiteLoginStatusService(manager)
    payload = svc.test_site_login_status('youtube')

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
