from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import services.site_runtime_service as plugin_service
from site_runtimes.runtime_models import PluginManifest, PluginSiteManifest
from routes.site_runtimes import build_site_info


def test_build_site_info_includes_icon_url():
    catalog = {
        'youtube': {
            'label': 'YouTube',
            'domains': ['youtube.com', 'youtu.be'],
            'enabled': True,
            'test_url': 'https://www.youtube.com',
            'icon_url': '/api/site-runtimes/sites/youtube/icon',
        }
    }

    info = build_site_info('youtube', catalog)

    assert info == {
        'name': 'youtube',
        'site_name': 'youtube',
        'label': 'YouTube',
        'domains': ['youtube.com', 'youtu.be'],
        'primary_domain': 'youtu.be',
        'test_url': 'https://www.youtube.com',
        'config_enabled': True,
        'icon_url': '/api/site-runtimes/sites/youtube/icon',
    }


def test_normalize_plugin_item_includes_site_icon_url_from_catalog():
    manifest = PluginManifest(
        plugin_id='youtube',
        version='1.0.0',
        display_name='YouTube',
        sites=[
            PluginSiteManifest(
                site_name='youtube',
                domains=['youtube.com', 'youtu.be'],
                test_url='https://www.youtube.com',
            )
        ],
    )
    record = SimpleNamespace(
        plugin_id='youtube',
        version='1.0.0',
        enabled=True,
        status=SimpleNamespace(value='running'),
        manifest=manifest.to_dict(),
    )
    snapshot = SimpleNamespace(runtimes=[])

    normalized = plugin_service._normalize_plugin_item(
        record,
        snapshot,
        {'youtube': {'icon_url': '/api/site-runtimes/sites/youtube/icon'}},
    )

    assert normalized['sites'] == [{
        'site_name': 'youtube',
        'domains': ['youtube.com', 'youtu.be'],
        'test_url': 'https://www.youtube.com',
        'features': [],
        'metadata': {},
        'icon_url': '/api/site-runtimes/sites/youtube/icon',
    }]


