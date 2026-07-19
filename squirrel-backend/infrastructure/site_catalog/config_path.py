from __future__ import annotations

from pathlib import Path


def get_site_catalog_config_path(repo_root: Path | None = None) -> Path:
    """Return the shared site override file used by every backend process."""
    root = repo_root or Path(__file__).resolve().parents[3]
    return root / 'config' / 'sites.json'
