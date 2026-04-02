import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes import plugins as plugin_routes


def test_get_supported_sites_merges_runtime_sites_when_catalog_is_partial(monkeypatch):
    file_catalog = {
        'youtube': {
            'label': 'YouTube',
            'domains': ['youtube.com', 'youtu.be'],
            'enabled': True,
            'test_url': 'https://www.youtube.com',
            'icon_url': '/api/plugins/sites/youtube/icon',
        }
    }
    runtime_catalog = {
        'youtube': {
            'label': 'YouTube',
            'domains': ['youtube.com', 'youtu.be'],
            'enabled': True,
            'test_url': 'https://www.youtube.com',
        },
        'bilibili': {
            'label': 'Bilibili',
            'domains': ['bilibili.com'],
            'enabled': True,
            'test_url': 'https://www.bilibili.com',
        },
    }

    monkeypatch.setattr(
        plugin_routes.SiteCatalog,
        'get_catalog',
        classmethod(lambda cls: file_catalog),
    )
    monkeypatch.setattr(
        plugin_routes.SiteCatalog,
        '_build_from_manifests',
        classmethod(lambda cls: runtime_catalog),
    )
    monkeypatch.setattr(plugin_routes, 'get_login_supported_sites', lambda: {'bilibili'})

    response = plugin_routes.get_supported_sites()

    assert response['code'] == 0

    sites = response['data']['sites']
    site_names = {site['site_name'] for site in sites}
    assert site_names == {'youtube', 'bilibili'}

    youtube = next(site for site in sites if site['site_name'] == 'youtube')
    bilibili = next(site for site in sites if site['site_name'] == 'bilibili')

    assert youtube['icon_url'] == '/api/plugins/sites/youtube/icon'
    assert bilibili['domains'] == ['bilibili.com']
    assert bilibili['supports_login_status'] is True
