from __future__ import annotations

import json

import core.site_config_manager as cscm
from services import site_catalog_service as scm
from services.site_catalog_service import SiteCatalogService


def test_save_site_overrides_persists_override_only(monkeypatch, tmp_path):
    config_path = tmp_path / 'sites.json'

    monkeypatch.setattr(SiteCatalogService, '_config_path', classmethod(lambda cls: config_path))
    monkeypatch.setattr(
        'core.site_config_manager.build_runtime_site_catalog',
        lambda: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com', 'youtu.be'],
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            },
        },
    )
    monkeypatch.setattr(scm.SiteCatalog, 'load_override_catalog', classmethod(lambda cls: {}))
    monkeypatch.setattr(scm.SiteCatalog, 'set_override_catalog', lambda catalog: None)
    monkeypatch.setattr(cscm, 'apply_site_config_overrides', lambda catalog=None: None)
    monkeypatch.setattr(
        cscm,
        'get_effective_site_catalog',
        lambda catalog=None: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com', 'youtu.be'],
                'enabled': False,
                'proxy': {'read_timeout': 240.0},
            },
        },
    )

    result = SiteCatalogService.save_site_overrides(
        {
            'youtube': {
                'enabled': False,
                'proxy': {'read_timeout': 240.0},
            },
        }
    )

    assert result['youtube']['enabled'] is False
    saved = json.loads(config_path.read_text(encoding='utf-8'))
    assert saved == {
        'youtube': {
            'enabled': False,
            'proxy': {'read_timeout': 240.0},
        },
    }


def test_save_site_overrides_merges_patch_and_prunes_values_equal_to_plugin_defaults(monkeypatch, tmp_path):
    config_path = tmp_path / 'sites.json'
    config_path.write_text(
        json.dumps(
            {
                'youtube': {
                    'enabled': False,
                    'proxy': {'read_timeout': 240.0},
                },
            }
        ),
        encoding='utf-8',
    )

    monkeypatch.setattr(SiteCatalogService, '_config_path', classmethod(lambda cls: config_path))
    monkeypatch.setattr(
        'core.site_config_manager.build_runtime_site_catalog',
        lambda: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com', 'youtu.be'],
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            },
        },
    )
    monkeypatch.setattr(
        scm.SiteCatalog,
        'load_override_catalog',
        classmethod(lambda cls: {'youtube': {'enabled': False, 'proxy': {'read_timeout': 240.0}}}),
    )
    monkeypatch.setattr(scm.SiteCatalog, 'set_override_catalog', lambda catalog: None)
    monkeypatch.setattr(cscm, 'apply_site_config_overrides', lambda catalog=None: None)
    monkeypatch.setattr(
        cscm,
        'get_effective_site_catalog',
        lambda catalog=None: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com', 'youtu.be'],
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            },
        },
    )

    result = SiteCatalogService.save_site_overrides(
        {
            'youtube': {
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            },
        }
    )

    assert result['youtube']['enabled'] is True
    saved = json.loads(config_path.read_text(encoding='utf-8'))
    assert saved == {}
