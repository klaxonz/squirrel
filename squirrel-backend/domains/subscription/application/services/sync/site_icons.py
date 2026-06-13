from __future__ import annotations

from collections.abc import Callable

from infrastructure.site_catalog.cache import get_cached_site_catalog
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.icons import build_site_icon_url, resolve_site_icon_path


class SiteIconResolver:
    def __init__(self, catalog_provider: Callable[[], dict[str, dict]] = get_cached_site_catalog):
        self.catalog_provider = catalog_provider
        self._site_icon_url_cache: dict[str, str | None] = {}

    @staticmethod
    def _find_catalog_entry(catalog: dict[str, dict], normalized_site: str) -> tuple[str | None, dict | None]:
        if normalized_site in catalog:
            return normalized_site, catalog[normalized_site]

        for slug, site_info in catalog.items():
            aliases = {str(alias or '').strip().lower() for alias in site_info.get('aliases', []) if alias}
            domains = {str(domain or '').strip().lower() for domain in site_info.get('domains', []) if domain}
            if normalized_site in aliases or normalized_site in domains:
                return slug, site_info

        site_slug, catalog_entry = SiteCatalog.find_site_by_domain(normalized_site)
        if site_slug and catalog_entry:
            return site_slug, catalog_entry

        return None, None

    def resolve(self, site: str | None) -> str | None:
        normalized_site = str(site or '').strip().lower()
        if not normalized_site:
            return None

        cached_icon_url = self._site_icon_url_cache.get(normalized_site)
        if normalized_site in self._site_icon_url_cache:
            return cached_icon_url

        catalog = self.catalog_provider()
        site_slug, catalog_entry = self._find_catalog_entry(catalog, normalized_site)

        icon_url = str((catalog_entry or {}).get('icon_url') or '').strip() or None
        if icon_url:
            self._site_icon_url_cache[normalized_site] = icon_url
            return icon_url

        resolved_slug = site_slug or normalized_site
        if resolve_site_icon_path(resolved_slug):
            resolved_icon_url = build_site_icon_url(resolved_slug)
            self._site_icon_url_cache[normalized_site] = resolved_icon_url
            return resolved_icon_url

        self._site_icon_url_cache[normalized_site] = None
        return None
