from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.site_catalog.runtime import SiteRuntimeService
from services.site_catalog.service import SiteCatalogService
from site_runtimes.runtime_models import SiteRuntimeManifest, SiteRuntimeSite


def test_build_site_info_includes_icon_url():
    catalog = {
        "youtube": {
            "label": "YouTube",
            "domains": ["youtube.com", "youtu.be"],
            "enabled": True,
            "test_url": "https://www.youtube.com",
            "icon_url": "/api/sites/youtube/icon",
        },
    }

    info = SiteCatalogService.build_site_info('youtube', catalog)

    assert info == {
        "name": "youtube",
        "site_name": "youtube",
        "label": "YouTube",
        "domains": ["youtube.com", "youtu.be"],
        "primary_domain": "youtu.be",
        "test_url": "https://www.youtube.com",
        "config_enabled": True,
        "icon_url": "/api/sites/youtube/icon",
    }


def test_normalize_runtime_item_includes_site_icon_url_from_catalog():
    manifest = SiteRuntimeManifest(
        runtime_id="youtube",
        version="1.0.0",
        display_name="YouTube",
        sites=[
            SiteRuntimeSite(
                site_name="youtube",
                domains=["youtube.com", "youtu.be"],
                test_url="https://www.youtube.com",
            ),
        ],
    )
    record = SimpleNamespace(
        runtime_id="youtube",
        version="1.0.0",
        enabled=True,
        status=SimpleNamespace(value="running"),
        manifest=manifest.to_dict(),
    )
    snapshot = SimpleNamespace(runtimes=[])

    normalized = SiteRuntimeService._normalize_runtime_item(
        record,
        snapshot,
        {"youtube": {"icon_url": "/api/sites/youtube/icon"}},
    )

    assert normalized["sites"] == [{
        "site_name": "youtube",
        "domains": ["youtube.com", "youtu.be"],
        "test_url": "https://www.youtube.com",
        "features": [],
        "metadata": {},
        "icon_url": "/api/sites/youtube/icon",
    }]


