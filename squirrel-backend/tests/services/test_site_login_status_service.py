from infrastructure.site_catalog.login_status import SiteLoginStatusService
from infrastructure.site_plugins.registry import SitePluginResult


def test_get_supported_sites_reads_login_status_registrations():
    class _Registry:
        def get_supported_sites(self, capability):
            return {'youtube', 'bilibili'} if capability == 'check_login_status' else set()

    svc = SiteLoginStatusService(_Registry())

    result = svc.get_supported_sites()

    assert result == {'youtube', 'bilibili'}


def test_test_site_login_status_returns_fallback_when_route_missing():
    class _Registry:
        def has_capability(self, site_name, capability):
            return False

    svc = SiteLoginStatusService(_Registry())
    payload = svc.test_site_login_status('youtube')

    assert payload['site_name'] == 'youtube'
    assert payload['supported'] is False
    assert payload['logged_in'] is False
    assert payload['message'] == 'login check not supported for this site'
    assert payload['checked_at']


def test_test_site_login_status_normalizes_runtime_payload():
    calls = []

    class _Registry:
        def has_capability(self, site_name, capability):
            return True

        def invoke(self, capability, payload=None, site_name=None, domain=None):
            calls.append({
                'capability': capability,
                'payload': payload,
                'site_name': site_name,
                'domain': domain,
            })
            return SitePluginResult(
                ok=True,
                data={
                    'logged_in': True,
                    'message': 'ok',
                    'extra': {'account': 'demo'},
                },
            )

    svc = SiteLoginStatusService(_Registry())
    payload = svc.test_site_login_status('youtube')

    assert calls == [{
        'capability': 'check_login_status',
        'payload': None,
        'site_name': 'youtube',
        'domain': None,
    }]
    assert payload['site_name'] == 'youtube'
    assert payload['supported'] is True
    assert payload['logged_in'] is True
    assert payload['message'] == 'ok'
    assert payload['extra'] == {'account': 'demo'}
    assert payload['checked_at']
