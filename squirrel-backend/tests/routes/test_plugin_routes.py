import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes import plugins as plugin_routes


def test_get_supported_sites_merges_runtime_sites_when_catalog_is_partial(monkeypatch):
    effective_catalog = {
        'youtube': {
            'label': 'YouTube',
            'domains': ['youtube.com', 'youtu.be'],
            'enabled': True,
            'test_url': 'https://www.youtube.com',
            'icon_url': '/api/plugins/sites/youtube/icon',
        },
        'bilibili': {
            'label': 'Bilibili',
            'domains': ['bilibili.com'],
            'enabled': True,
            'test_url': 'https://www.bilibili.com',
        },
    }

    monkeypatch.setattr(plugin_routes, 'get_effective_site_catalog', lambda: effective_catalog)
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


def test_upload_site_cookies_accepts_runtime_only_site(monkeypatch, tmp_path):
    effective_catalog = {
        'youporn': {
            'label': 'YouPorn',
            'domains': ['youporn.com'],
            'enabled': True,
            'test_url': 'https://www.youporn.com',
        }
    }
    cookies_path = tmp_path / 'youporn.txt'

    monkeypatch.setattr(plugin_routes, 'get_effective_site_catalog', lambda: effective_catalog)
    monkeypatch.setattr(plugin_routes, 'get_site_cookies_file_path', lambda site_name: cookies_path)
    monkeypatch.setattr(
        plugin_routes,
        'test_site_login_status',
        lambda site_name: {'supported': True, 'logged_in': True, 'site_name': site_name},
    )

    class DummyUploadFile:
        filename = 'cookies.txt'

        async def read(self):
            return (
                '# Netscape HTTP Cookie File\n'
                '.youporn.com\tTRUE\t/\tFALSE\t0\tsession\tabc123\n'
            ).encode('utf-8')

    response = asyncio.run(plugin_routes.upload_site_cookies('youporn', DummyUploadFile()))

    assert response['code'] == 0
    assert response['data']['site_name'] == 'youporn'
    assert '.youporn.com' in cookies_path.read_text(encoding='utf-8')
