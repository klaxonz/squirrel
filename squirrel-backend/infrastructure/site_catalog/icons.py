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
    return f'/api/sites/{slug}/icon'


def normalize_site_icon_url(site_name: str | None, icon_url: object) -> str | None:
    """Preserve custom icons while migrating the removed plugin-icon route."""
    value = str(icon_url or '').strip()
    if not value:
        return None

    slug = normalize_site_slug(site_name)
    legacy_url = f'/api/plugins/sites/{slug}/icon' if slug else ''
    if legacy_url and value == legacy_url:
        return build_site_icon_url(slug)
    return value


def resolve_site_icon_path(site_name: str | None) -> Path | None:
    slug = normalize_site_slug(site_name)
    if not slug:
        return None

    # icons.py lives at squirrel-backend/infrastructure/site_catalog/icons.py
    # parents[2] = squirrel-backend, parents[3] = monorepo root (where
    # squirrel-site-runtimes actually lives). Prefer repo root; fall back to
    # backend-local layout for alternate packaging.
    here = Path(__file__).resolve()
    candidates = (
        here.parents[3] / 'squirrel-site-runtimes',
        here.parents[2] / 'squirrel-site-runtimes',
    )

    for base_runtimes in candidates:
        if not base_runtimes.is_dir():
            continue
        assets_dir = (base_runtimes / slug / 'assets').resolve()
        try:
            if not assets_dir.is_relative_to(base_runtimes.resolve()):
                continue
        except (OSError, ValueError):
            continue
        if not assets_dir.is_dir():
            continue
        for filename in SITE_ICON_FILENAMES:
            candidate = assets_dir / filename
            if candidate.is_file():
                return candidate
    return None
