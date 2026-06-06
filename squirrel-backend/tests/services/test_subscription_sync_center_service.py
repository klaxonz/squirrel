from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services import subscription_sync_center_service


def test_get_cached_site_catalog_reuses_cached_result_within_ttl(monkeypatch):
    monkeypatch.setattr(subscription_sync_center_service, '_site_catalog_cache', None, raising=False)
    monkeypatch.setattr(subscription_sync_center_service, '_site_catalog_cache_expires_at_monotonic', None, raising=False)
    monkeypatch.setattr(subscription_sync_center_service, '_site_icon_url_cache', {}, raising=False)

    monotonic_values = iter([100.0, 100.1, 105.0])
    calls = []

    def _fake_get_effective_site_catalog():
        calls.append(1)
        return {
            'youtube': {
                'domains': ['youtube.com'],
                'icon_url': '/api/site-runtimes/sites/youtube/icon',
            }
        }

    monkeypatch.setattr(subscription_sync_center_service, 'monotonic', lambda: next(monotonic_values))
    monkeypatch.setattr(subscription_sync_center_service, 'get_effective_site_catalog', _fake_get_effective_site_catalog)

    first = subscription_sync_center_service._get_cached_site_catalog()
    second = subscription_sync_center_service._get_cached_site_catalog()

    assert first == second
    assert first['youtube']['icon_url'] == '/api/site-runtimes/sites/youtube/icon'
    assert len(calls) == 1

