from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services import site_catalog_service


def test_save_sites_preserves_icon_url(monkeypatch, tmp_path):
    config_path = tmp_path / 'sites.json'

    monkeypatch.setattr(site_catalog_service, '_config_path', lambda: config_path)
    monkeypatch.setattr(site_catalog_service.SiteCatalog, 'set_catalog', lambda catalog: None)
    monkeypatch.setattr(site_catalog_service, 'apply_site_config_overrides', lambda catalog: None)
    monkeypatch.setattr(site_catalog_service, 'get_effective_site_catalog', lambda catalog: catalog)

    payload = [{
        'slug': 'youtube',
        'label': 'YouTube',
        'domains': ['youtube.com', 'youtu.be'],
        'aliases': ['yt'],
        'enabled': True,
        'test_url': 'https://www.youtube.com',
        'icon_url': '/api/plugins/sites/youtube/icon',
    }]

    result = site_catalog_service.save_sites(payload)

    assert result['youtube']['icon_url'] == '/api/plugins/sites/youtube/icon'
    saved = json.loads(config_path.read_text(encoding='utf-8'))
    assert saved['youtube']['icon_url'] == '/api/plugins/sites/youtube/icon'
