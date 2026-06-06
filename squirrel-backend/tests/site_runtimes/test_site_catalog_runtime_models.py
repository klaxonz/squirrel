from pathlib import Path
import json
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from site_runtimes.runtime_models import SiteRuntimeCapability, SiteRuntimeManifest, SiteRuntimeSite
from utils.site_catalog import SiteCatalog


def test_site_catalog_builds_from_backend_runtime_manifest_models(monkeypatch):
    manifest = SiteRuntimeManifest(
        runtime_id='youtube',
        version='0.1.0',
        display_name='YouTube',
        capabilities=[SiteRuntimeCapability(name='extract_video')],
        sites=[
            SiteRuntimeSite(
                site_name='youtube',
                domains=['youtube.com', 'youtu.be'],
                test_url='https://www.youtube.com',
                features=['extract_video', 'fetch_subtitles'],
            )
        ],
    )

    monkeypatch.setattr(
        'utils.site_catalog.get_site_runtime_manager',
        lambda: SimpleNamespace(
            get_snapshot=lambda: SimpleNamespace(
                records=[
                    SimpleNamespace(
                        enabled=True,
                        manifest=manifest.to_dict(),
                    )
                ]
            )
        ),
    )

    catalog = SiteCatalog._build_from_manifests()

    assert catalog == {
        'youtube': {
            'label': 'youtube',
            'domains': ['youtube.com', 'youtu.be'],
            'aliases': [],
            'enabled': True,
            'features': ['extract_video', 'fetch_subtitles'],
            'test_url': 'https://www.youtube.com',
            'icon_url': '/api/sites/youtube/icon',
        }
    }


def test_site_catalog_builds_site_defaults_from_manifest_metadata(monkeypatch):
    manifest = SiteRuntimeManifest(
        runtime_id='youtube',
        version='0.1.0',
        display_name='YouTube',
        capabilities=[SiteRuntimeCapability(name='extract_video')],
        sites=[
            SiteRuntimeSite(
                site_name='youtube',
                domains=['youtube.com', 'youtu.be'],
                test_url='https://www.youtube.com',
                features=['extract_video'],
                metadata={
                    'label': 'YouTube',
                    'aliases': ['yt'],
                    'http': {'headers': {'User-Agent': 'UA'}},
                    'rate_limit': {'enabled': True, 'min_interval': 2.0, 'max_interval': 5.0},
                    'metadata': {'requires_cookies': False},
                },
            )
        ],
    )

    monkeypatch.setattr(
        'utils.site_catalog.get_site_runtime_manager',
        lambda: SimpleNamespace(
            get_snapshot=lambda: SimpleNamespace(
                records=[
                    SimpleNamespace(
                        enabled=True,
                        manifest=manifest.to_dict(),
                    )
                ]
            )
        ),
    )

    catalog = SiteCatalog.build_runtime_site_catalog()

    assert catalog['youtube']['label'] == 'YouTube'
    assert catalog['youtube']['aliases'] == ['yt']
    assert catalog['youtube']['http']['headers']['User-Agent'] == 'UA'
    assert catalog['youtube']['domains'] == ['youtube.com', 'youtu.be']


def test_site_catalog_builds_icon_url_from_plugin_assets_when_metadata_does_not_define_it(monkeypatch):
    manifest = SiteRuntimeManifest(
        runtime_id='youporn',
        version='0.1.0',
        display_name='YouPorn',
        capabilities=[SiteRuntimeCapability(name='extract_video')],
        sites=[
            SiteRuntimeSite(
                site_name='youporn',
                domains=['youporn.com'],
                test_url='https://www.youporn.com',
                metadata={
                    'label': 'YouPorn',
                    'aliases': ['yp'],
                },
            )
        ],
    )

    monkeypatch.setattr(
        'utils.site_catalog.get_site_runtime_manager',
        lambda: SimpleNamespace(
            get_snapshot=lambda: SimpleNamespace(
                records=[
                    SimpleNamespace(
                        enabled=True,
                        manifest=manifest.to_dict(),
                    )
                ]
            )
        ),
    )
    monkeypatch.setattr('utils.site_catalog.resolve_site_icon_path', lambda site_name: Path(f'/tmp/{site_name}.png'))
    monkeypatch.setattr('utils.site_catalog.build_site_icon_url', lambda site_name: f'/api/sites/{site_name}/icon')

    catalog = SiteCatalog.build_runtime_site_catalog()

    assert catalog['youporn']['icon_url'] == '/api/sites/youporn/icon'


def test_site_catalog_load_from_file_preserves_icon_url(monkeypatch, tmp_path):
    config_path = tmp_path / 'sites.json'
    config_path.write_text(json.dumps({
        'youtube': {
            'label': 'YouTube',
            'domains': ['youtube.com', 'youtu.be'],
            'aliases': ['yt'],
            'enabled': True,
            'test_url': 'https://www.youtube.com',
            'icon_url': '/api/sites/youtube/icon',
        }
    }), encoding='utf-8')

    monkeypatch.setattr(SiteCatalog, '_config_path', staticmethod(lambda: str(config_path)))

    catalog = SiteCatalog._load_from_file()

    assert catalog is not None
    assert catalog['youtube']['label'] == 'YouTube'
    assert set(catalog['youtube']['domains']) == {'youtube.com', 'youtu.be'}
    assert catalog['youtube']['aliases'] == ['yt']
    assert catalog['youtube']['enabled'] is True
    assert catalog['youtube']['test_url'] == 'https://www.youtube.com'
    assert catalog['youtube']['icon_url'] == '/api/sites/youtube/icon'


def test_site_catalog_load_from_file_keeps_sparse_overrides_sparse(monkeypatch, tmp_path):
    config_path = tmp_path / 'sites.json'
    config_path.write_text(json.dumps({
        'youporn': {
            'metadata': {
                'offline_thumbnails_display': False,
            }
        }
    }), encoding='utf-8')

    monkeypatch.setattr(SiteCatalog, '_config_path', staticmethod(lambda: str(config_path)))

    catalog = SiteCatalog._load_from_file()

    assert catalog is not None
    assert catalog['youporn'] == {
        'metadata': {
            'offline_thumbnails_display': False,
        }
    }


