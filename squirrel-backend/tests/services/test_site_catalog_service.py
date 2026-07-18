from __future__ import annotations

import json
from unittest.mock import patch

from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.service import SiteCatalogService


def test_save_site_overrides_persists_override_only(tmp_path):
    config_path = tmp_path / 'sites.json'

    with (
        patch.object(SiteCatalogService, '_config_path', return_value=config_path),
        patch(
            'infrastructure.site_catalog.service.build_plugin_site_catalog',
            return_value={
                'youtube': {
                    'label': 'YouTube',
                    'domains': ['youtube.com', 'youtu.be'],
                    'enabled': True,
                    'proxy': {'read_timeout': 180.0},
                },
            },
        ),
        patch('infrastructure.site_catalog.catalog.SiteCatalog.load_override_catalog', return_value={}),
        patch('infrastructure.site_catalog.catalog.SiteCatalog.set_override_catalog'),
        patch('infrastructure.site_catalog.service.apply_site_config_overrides'),
        patch(
            'infrastructure.site_catalog.service.get_effective_site_catalog',
            return_value={
                'youtube': {
                    'label': 'YouTube',
                    'domains': ['youtube.com', 'youtu.be'],
                    'enabled': False,
                    'proxy': {'read_timeout': 240.0},
                },
            },
        ),
    ):
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


def test_save_site_overrides_merges_patch_and_prunes_values_equal_to_plugin_defaults(tmp_path):
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

    with (
        patch.object(SiteCatalogService, '_config_path', return_value=config_path),
        patch(
            'infrastructure.site_catalog.service.build_plugin_site_catalog',
            return_value={
                'youtube': {
                    'label': 'YouTube',
                    'domains': ['youtube.com', 'youtu.be'],
                    'enabled': True,
                    'proxy': {'read_timeout': 180.0},
                },
            },
        ),
        patch(
            'infrastructure.site_catalog.catalog.SiteCatalog.load_override_catalog',
            return_value={'youtube': {'enabled': False, 'proxy': {'read_timeout': 240.0}}},
        ),
        patch('infrastructure.site_catalog.catalog.SiteCatalog.set_override_catalog'),
        patch('infrastructure.site_catalog.service.apply_site_config_overrides'),
        patch(
            'infrastructure.site_catalog.service.get_effective_site_catalog',
            return_value={
                'youtube': {
                    'label': 'YouTube',
                    'domains': ['youtube.com', 'youtu.be'],
                    'enabled': True,
                    'proxy': {'read_timeout': 180.0},
                },
            },
        ),
    ):
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


def test_load_site_overrides_migrates_removed_plugin_icon_route(tmp_path):
    config_path = tmp_path / 'sites.json'
    config_path.write_text(
        json.dumps(
            {
                'youtube': {'icon_url': '/api/plugins/sites/youtube/icon'},
                'custom': {'icon_url': 'https://cdn.example.com/custom.png'},
            }
        ),
        encoding='utf-8',
    )

    with patch.object(SiteCatalog, '_config_path', return_value=str(config_path)):
        catalog = SiteCatalog.load_override_catalog()

    assert catalog is not None
    assert catalog['youtube']['icon_url'] == '/api/sites/youtube/icon'
    assert catalog['custom']['icon_url'] == 'https://cdn.example.com/custom.png'
