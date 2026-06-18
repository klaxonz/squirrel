from __future__ import annotations

from typing import Any

from infrastructure.runtime.site_config_manager import get_effective_site_catalog
from infrastructure.site_catalog.service import SiteCatalogService
from infrastructure.site_plugins.registry import SitePluginRegistry, get_site_plugin_registry


class SitePluginService:
    def __init__(self, registry: SitePluginRegistry | None = None) -> None:
        self._registry = registry or get_site_plugin_registry()

    @staticmethod
    def _normalize_plugin_item(plugin: dict[str, Any], catalog: dict[str, dict]) -> dict[str, Any]:
        sites = []
        enabled = True
        for site in plugin.get('sites') or []:
            payload = dict(site)
            site_name = str(payload.get('site_name') or '').strip().lower()
            catalog_entry = catalog.get(site_name) or {}
            payload['enabled'] = catalog_entry.get('enabled', True)
            if catalog_entry.get('icon_url'):
                payload['icon_url'] = catalog_entry['icon_url']
            enabled = enabled and bool(payload['enabled'])
            sites.append(payload)

        return {
            **plugin,
            'enabled': enabled,
            'status': 'enabled' if enabled else 'disabled',
            'sites': sites,
        }

    def list_site_plugins(self) -> dict[str, Any]:
        catalog = get_effective_site_catalog()
        return {
            'items': [
                self._normalize_plugin_item(plugin, catalog)
                for plugin in self._registry.list_plugins()
            ],
            'errors': [],
        }

    def set_enabled_by_name(self, name: str, enabled: bool) -> bool:
        slug = str(name or '').strip().lower()
        if slug not in self._registry.build_site_catalog():
            return False
        SiteCatalogService().save_site_overrides({slug: {'enabled': enabled}})
        return True
