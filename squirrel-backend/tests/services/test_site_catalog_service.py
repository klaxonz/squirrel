from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services import site_catalog_service


def test_save_site_overrides_persists_override_only(monkeypatch, tmp_path):
    config_path = tmp_path / 'sites.json'

    monkeypatch.setattr(site_catalog_service, '_config_path', lambda: config_path)
    monkeypatch.setattr(
        site_catalog_service,
        'build_plugin_site_catalog',
        lambda: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com', 'youtu.be'],
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            }
        },
        raising=False,
    )
    monkeypatch.setattr(site_catalog_service.SiteCatalog, 'load_override_catalog', classmethod(lambda cls: {}), raising=False)
    monkeypatch.setattr(site_catalog_service.SiteCatalog, 'set_override_catalog', lambda catalog: None, raising=False)
    monkeypatch.setattr(site_catalog_service, 'apply_site_config_overrides', lambda catalog=None: None)
    monkeypatch.setattr(
        site_catalog_service,
        'get_effective_site_catalog',
        lambda catalog=None: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com', 'youtu.be'],
                'enabled': False,
                'proxy': {'read_timeout': 240.0},
            }
        },
    )

    result = site_catalog_service.save_site_overrides({
        'youtube': {
            'enabled': False,
            'proxy': {'read_timeout': 240.0},
        }
    })

    assert result['youtube']['enabled'] is False
    saved = json.loads(config_path.read_text(encoding='utf-8'))
    assert saved == {
        'youtube': {
            'enabled': False,
            'proxy': {'read_timeout': 240.0},
        }
    }


def test_save_site_overrides_merges_patch_and_prunes_values_equal_to_plugin_defaults(monkeypatch, tmp_path):
    config_path = tmp_path / 'sites.json'
    config_path.write_text(
        json.dumps({
            'youtube': {
                'enabled': False,
                'proxy': {'read_timeout': 240.0},
            }
        }),
        encoding='utf-8',
    )

    monkeypatch.setattr(site_catalog_service, '_config_path', lambda: config_path)
    monkeypatch.setattr(
        site_catalog_service,
        'build_plugin_site_catalog',
        lambda: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com', 'youtu.be'],
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            }
        },
        raising=False,
    )
    monkeypatch.setattr(
        site_catalog_service.SiteCatalog,
        'load_override_catalog',
        classmethod(
            lambda cls: {
                'youtube': {
                    'enabled': False,
                    'proxy': {'read_timeout': 240.0},
                }
            }
        ),
        raising=False,
    )
    monkeypatch.setattr(site_catalog_service.SiteCatalog, 'set_override_catalog', lambda catalog: None, raising=False)
    monkeypatch.setattr(site_catalog_service, 'apply_site_config_overrides', lambda catalog=None: None)
    monkeypatch.setattr(
        site_catalog_service,
        'get_effective_site_catalog',
        lambda catalog=None: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com', 'youtu.be'],
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            }
        },
    )

    result = site_catalog_service.save_site_overrides({
        'youtube': {
            'enabled': True,
            'proxy': {'read_timeout': 180.0},
        }
    })

    assert result['youtube']['enabled'] is True
    saved = json.loads(config_path.read_text(encoding='utf-8'))
    assert saved == {}
