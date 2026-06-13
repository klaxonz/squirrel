import json
from pathlib import Path

from infrastructure.config.site_config_manager import apply_site_config_overrides, build_runtime_site_catalog, get_effective_site_catalog
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.icons import build_site_icon_url, resolve_site_icon_path
from infrastructure.site_catalog.overrides import compute_override_diff, deep_merge_dicts, normalize_override_entry


class SiteCatalogService:
    @staticmethod
    def normalize_cookie_domain(domain: str) -> str:
        if not domain:
            return ''
        d = str(domain).strip()
        if d.startswith('#HttpOnly_'):
            d = d[len('#HttpOnly_'):]
        return d.lstrip('.').lower()

    @staticmethod
    def select_primary_domain(domains: list) -> str | None:
        if not domains:
            return None
        www_domains = [d for d in domains if d.startswith('www.')]
        if www_domains:
            return www_domains[0]
        return min(domains, key=len)

    @staticmethod
    def merge_site_names(catalog: dict) -> list[str]:
        names: list[str] = []
        seen = set()
        for slug in catalog:
            key = slug.lower()
            if key in seen:
                continue
            seen.add(key)
            names.append(slug)
        return names

    @staticmethod
    def merge_site_catalogs(*catalogs: dict | None) -> dict:
        merged: dict = {}
        for catalog in catalogs:
            for raw_slug, raw_info in (catalog or {}).items():
                slug = str(raw_slug or '').strip().lower()
                if not slug:
                    continue
                incoming = dict(raw_info or {})
                existing = merged.get(slug, {})
                merged_entry = dict(existing)
                if 'label' in incoming or 'label' not in merged_entry:
                    merged_entry['label'] = incoming.get('label') or merged_entry.get('label') or raw_slug
                merged_entry['enabled'] = bool(incoming.get('enabled', merged_entry.get('enabled', True)))
                for key in ('test_url', 'icon_url'):
                    value = incoming.get(key)
                    if value:
                        merged_entry[key] = value
                for key in ('domains', 'aliases', 'features'):
                    seen = set()
                    values = []
                    for item in list(merged_entry.get(key) or []) + list(incoming.get(key) or []):
                        normalized = str(item or '').strip().lower()
                        if not normalized or normalized in seen:
                            continue
                        seen.add(normalized)
                        values.append(normalized)
                    merged_entry[key] = values
                for key, value in incoming.items():
                    if key in {'label', 'enabled', 'test_url', 'icon_url', 'domains', 'aliases', 'features'}:
                        continue
                    if value is not None:
                        merged_entry[key] = value
                merged[slug] = merged_entry
        return merged

    @staticmethod
    def build_site_info(site_name: str, catalog: dict) -> dict | None:
        if not site_name:
            return None
        slug = site_name.lower()
        catalog_entry = catalog.get(slug, {})
        site_domains = catalog_entry.get('domains') or []
        seen = set()
        deduped_domains = []
        for d in site_domains:
            if d in seen:
                continue
            seen.add(d)
            deduped_domains.append(d)
        primary_domain = SiteCatalogService.select_primary_domain(deduped_domains)
        test_url = (
            catalog_entry.get('test_url')
            or (f'https://{primary_domain}' if primary_domain else None)
        )
        icon_url = catalog_entry.get('icon_url')
        if not icon_url and resolve_site_icon_path(site_name):
            icon_url = build_site_icon_url(site_name)
        return {
            'name': site_name,
            'site_name': site_name,
            'label': catalog_entry.get('label', site_name),
            'domains': deduped_domains,
            'primary_domain': primary_domain,
            'test_url': test_url,
            'config_enabled': catalog_entry.get('enabled', True),
            'icon_url': icon_url,
        }

    @staticmethod
    def get_merged_site_catalog() -> dict:
        return get_effective_site_catalog()

    @staticmethod
    def save_site_overrides(overrides: dict[str, dict]) -> dict[str, dict]:
        if not isinstance(overrides, dict):
            raise ValueError('sites must be a dict')

        plugin_catalog = build_runtime_site_catalog()
        existing_overrides = SiteCatalog.load_override_catalog() or {}
        current_effective = get_effective_site_catalog(existing_overrides)
        catalog: dict[str, dict] = dict(existing_overrides)
        for raw_slug, raw in overrides.items():
            slug = str(raw_slug or '').strip().lower()
            if not slug:
                raise ValueError('site slug is required')
            if slug not in plugin_catalog:
                raise ValueError(f'unknown site: {slug}')
            normalized_patch = normalize_override_entry(slug, raw)
            desired_effective = deep_merge_dicts(
                current_effective.get(slug, plugin_catalog[slug]), normalized_patch,
            )
            normalized_entry = compute_override_diff(plugin_catalog[slug], desired_effective)
            if normalized_entry:
                catalog[slug] = normalized_entry
            else:
                catalog.pop(slug, None)

        config_path = SiteCatalogService._config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        SiteCatalog.set_override_catalog(catalog)
        apply_site_config_overrides(catalog)
        return get_effective_site_catalog(catalog)

    # --- private helpers ---

    @staticmethod
    def _config_path() -> Path:
        return Path(__file__).resolve().parents[2] / 'config' / 'sites.json'
