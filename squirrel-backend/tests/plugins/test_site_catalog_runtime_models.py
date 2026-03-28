from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from plugins.runtime_models import PluginCapability, PluginManifest, PluginSiteManifest
from utils.site_catalog import SiteCatalog


def test_site_catalog_builds_from_backend_runtime_manifest_models(monkeypatch):
    manifest = PluginManifest(
        plugin_id='youtube',
        version='0.1.0',
        display_name='YouTube',
        capabilities=[PluginCapability(name='extract_video')],
        sites=[
            PluginSiteManifest(
                site_name='youtube',
                domains=['youtube.com', 'youtu.be'],
                test_url='https://www.youtube.com',
                features=['extract_video', 'resolve_playback'],
            )
        ],
    )

    monkeypatch.setattr(
        'utils.site_catalog.get_plugin_manager',
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
            'features': ['extract_video', 'resolve_playback'],
            'test_url': 'https://www.youtube.com',
        }
    }
