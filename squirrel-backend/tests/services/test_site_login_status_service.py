from types import SimpleNamespace

from infrastructure.site_catalog.login_status import SiteLoginStatusService
from sites.crawl import AuthError


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

    class _FakeRuntime:
        def check_login_status(self):
            calls.append('check_login_status')
            return SimpleNamespace(
                to_dict=lambda: {'logged_in': True, 'message': 'ok', 'extra': {'account': 'demo'}}
            )

    class _Registry:
        def has_capability(self, site_name, capability):
            return True

        def get_site_runtime(self, site_name):
            calls.append(site_name)
            return _FakeRuntime()

    svc = SiteLoginStatusService(_Registry())
    payload = svc.test_site_login_status('youtube')

    assert calls == ['youtube', 'check_login_status']
    assert payload['site_name'] == 'youtube'
    assert payload['supported'] is True
    assert payload['logged_in'] is True
    assert payload['message'] == 'ok'
    assert payload['extra'] == {'account': 'demo'}
    assert payload['checked_at']


def test_test_site_login_status_maps_crawl_error_to_failure():
    class _FakeRuntime:
        def check_login_status(self):
            raise AuthError('login required')

    class _Registry:
        def has_capability(self, site_name, capability):
            return True

        def get_site_runtime(self, site_name):
            return _FakeRuntime()

    svc = SiteLoginStatusService(_Registry())
    payload = svc.test_site_login_status('youtube')

    assert payload['site_name'] == 'youtube'
    assert payload['supported'] is True
    assert payload['logged_in'] is False
    assert payload['message'] == 'login required'
    assert payload['checked_at']
