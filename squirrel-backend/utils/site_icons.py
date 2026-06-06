from __future__ import annotations

from pathlib import Path

SITE_ICON_FILENAMES = (
    'icon.svg',
    'icon.png',
    'icon.ico',
    'icon.jpg',
    'icon.jpeg',
    'icon.webp',
)


def normalize_site_slug(site_name: str | None) -> str:
    return str(site_name or '').strip().lower()


def build_site_icon_url(site_name: str | None) -> str | None:
    slug = normalize_site_slug(site_name)
    if not slug:
        return None
    return f'/api/site-runtimes/sites/{slug}/icon'


def resolve_site_icon_path(site_name: str | None) -> Path | None:
    slug = normalize_site_slug(site_name)
    if not slug:
        return None

    assets_dir = Path(__file__).resolve().parents[2] / 'squirrel-plugins' / slug / 'assets'
    if not assets_dir.exists():
        return None

    for filename in SITE_ICON_FILENAMES:
        candidate = assets_dir / filename
        if candidate.is_file():
            return candidate
    return None

