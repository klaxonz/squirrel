from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SitePluginError:
    message: str
    details: dict[str, Any]
    retryable: bool = False


@dataclass(frozen=True)
class SitePluginResult:
    ok: bool
    data: Any = None
    error: SitePluginError | None = None
    retryable: bool = False


@dataclass(frozen=True)
class _PluginDefinition:
    package_dir: str
    module_name: str


_PLUGIN_DEFINITIONS = {
    'bilibili': _PluginDefinition('bilibili', 'squirrel_bilibili.runtime'),
    'javdb': _PluginDefinition('javdb', 'squirrel_javdb.runtime'),
    'pornhub': _PluginDefinition('pornhub', 'squirrel_pornhub.runtime'),
    'youtube': _PluginDefinition('youtube', 'squirrel_youtube.runtime'),
    'youporn': _PluginDefinition('youporn', 'squirrel_youporn.runtime'),
}


class SitePluginRegistry:
    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._plugins: dict[str, Any] = {}

    @property
    def _runtimes_root(self) -> Path:
        return self._repo_root / 'squirrel-site-runtimes'

    def _install_import_paths(self) -> None:
        paths = [self._runtimes_root / 'shared']
        paths.extend(self._runtimes_root / item.package_dir / 'src' for item in _PLUGIN_DEFINITIONS.values())
        for path in reversed(paths):
            text = str(path)
            if text not in sys.path:
                sys.path.insert(0, text)

    def _load_plugin(self, site_name: str):
        slug = site_name.strip().lower()
        plugin = self._plugins.get(slug)
        if plugin is not None:
            return plugin

        definition = _PLUGIN_DEFINITIONS[slug]
        self._install_import_paths()
        module = import_module(definition.module_name)
        plugin = module.get_site_runtime()
        self._plugins[slug] = plugin
        return plugin

    def start_all(self) -> None:
        for site_name in _PLUGIN_DEFINITIONS:
            self._load_plugin(site_name).start({})

    def stop_all(self) -> None:
        for plugin in self._plugins.values():
            plugin.stop()

    def list_plugins(self) -> list[dict[str, Any]]:
        items = []
        for site_name in _PLUGIN_DEFINITIONS:
            plugin = self._load_plugin(site_name)
            manifest = plugin.manifest()
            items.append({
                'plugin_id': manifest.runtime_id,
                'display_name': manifest.display_name or manifest.runtime_id,
                'description': manifest.description,
                'version': manifest.version,
                'enabled': True,
                'capabilities': [item.to_dict() for item in manifest.capabilities],
                'sites': [item.to_dict() for item in manifest.sites],
            })
        return items

    def build_site_catalog(self) -> dict[str, dict]:
        catalog: dict[str, dict] = {}
        for site_name in _PLUGIN_DEFINITIONS:
            manifest = self._load_plugin(site_name).manifest()
            for site in manifest.sites:
                slug = site.site_name.strip().lower()
                defaults = dict(site.metadata or {})
                item = catalog.setdefault(slug, {
                    'label': defaults.get('label') or site.site_name,
                    'domains': [],
                    'aliases': [],
                    'enabled': True,
                    'features': [],
                })
                item['label'] = defaults.get('label') or item.get('label') or site.site_name
                if site.test_url:
                    item['test_url'] = site.test_url
                for alias in [str(alias).strip().lower() for alias in defaults.get('aliases') or [] if alias]:
                    if alias not in item['aliases']:
                        item['aliases'].append(alias)
                for key in ('http', 'proxy', 'login', 'rate_limit', 'cookie', 'metadata', 'icon_url'):
                    value = defaults.get(key)
                    if value is not None:
                        item[key] = value
                for feature in site.features:
                    if feature not in item['features']:
                        item['features'].append(feature)
                for domain in site.domains:
                    normalized = str(domain).strip().lower()
                    if normalized and normalized not in item['domains']:
                        item['domains'].append(normalized)
        return catalog

    def get_supported_sites(self, capability: str) -> set[str]:
        return {
            site.site_name
            for site_name in _PLUGIN_DEFINITIONS
            for site in self._load_plugin(site_name).manifest().sites
            if capability in set(site.features)
        }

    def has_capability(self, site_name: str, capability: str) -> bool:
        slug = site_name.strip().lower()
        if slug not in _PLUGIN_DEFINITIONS:
            return False
        return slug in self.get_supported_sites(capability)

    def find_site_by_domain(self, domain: str | None) -> str | None:
        if not domain:
            return None
        value = domain.split(':')[0].strip().lower()
        for slug, info in self.build_site_catalog().items():
            for configured_domain in info.get('domains') or []:
                configured = str(configured_domain).strip().lower()
                if value == configured or value.endswith(f'.{configured}'):
                    return slug
        return None

    def invoke(
        self,
        capability: str,
        payload: dict[str, Any] | None = None,
        *,
        site_name: str | None = None,
        domain: str | None = None,
    ) -> SitePluginResult:
        slug = site_name.strip().lower() if site_name else self.find_site_by_domain(domain)
        if not slug or not self.has_capability(slug, capability):
            raise ValueError(f'No plugin capability route found: capability={capability}, site={site_name}, domain={domain}')

        response = self._load_plugin(slug).invoke(capability, dict(payload or {}))
        error = getattr(response, 'error', None)
        return SitePluginResult(
            ok=bool(response.ok),
            data=response.data,
            error=None if error is None else SitePluginError(
                message=str(error.message),
                details=dict(error.details or {}),
                retryable=bool(error.retryable),
            ),
            retryable=bool(getattr(response, 'retryable', False)),
        )


_site_plugin_registry = SitePluginRegistry()


def get_site_plugin_registry() -> SitePluginRegistry:
    return _site_plugin_registry
