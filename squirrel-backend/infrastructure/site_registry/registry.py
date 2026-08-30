"""In-tree site registry.

Maps site slug -> importable module exposing ``get_site_runtime()``. The
runtime objects are plain typed Python objects (no manifest, no capability
RPC); this module only handles loading, caching, lifecycle hooks, and the
domain/capability queries the rest of the backend still asks for.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from contextlib import suppress
from pathlib import Path
from typing import Any

from sites.squirrel_bilibili.runtime import get_site_runtime as get_bilibili_site_runtime
from sites.squirrel_youtube.runtime import get_site_runtime as get_youtube_site_runtime

# Typed factories are registered explicitly so runtime loading does not use a
# string-based dynamic import boundary.
_SITE_DEFINITIONS: dict[str, Callable[[], Any]] = {
    'bilibili': get_bilibili_site_runtime,
    'youtube': get_youtube_site_runtime,
}

# The five typed methods every site runtime exposes (in registration order).
_SITE_CAPABILITIES = (
    'check_login_status',
    'import_subscriptions',
    'resolve_subscription',
    'sync_subscription',
    'extract_video',
)


class SiteRegistry:
    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._runtimes: dict[str, Any] = {}
        self._lock = threading.RLock()

    def get_site_runtime(self, site_name: str):
        """Load (and cache) the typed runtime object for a site slug."""
        slug = str(site_name or '').strip().lower()
        with self._lock:
            runtime = self._runtimes.get(slug)
            if runtime is not None:
                return runtime
            if slug not in _SITE_DEFINITIONS:
                raise ValueError(f'Unknown site: {slug!r}')
            runtime = _SITE_DEFINITIONS[slug]()
            self._runtimes[slug] = runtime
            return runtime

    def start_all(self) -> None:
        for slug in _SITE_DEFINITIONS:
            self.get_site_runtime(slug).start({})

    def stop_all(self) -> None:
        with self._lock:
            runtimes = list(self._runtimes.values())
            self._runtimes.clear()
        for runtime in runtimes:
            with suppress(Exception):
                runtime.stop()

    def refresh_sites(self, site_names: Iterable[str]) -> None:
        """Apply config updates for changed sites.

        Sites run in-process and read effective site config through the
        shared runtime-config module state (refreshed by
        ``apply_site_config_overrides``), so no restart is needed. Kept as a
        no-op for API/consumer compatibility.
        """
        for site_name in site_names:
            _ = str(site_name or '').strip().lower()

    def supported_sites(self) -> set[str]:
        return set(_SITE_DEFINITIONS)

    def get_supported_sites(self, capability: str) -> set[str]:
        return {slug for slug in _SITE_DEFINITIONS if hasattr(self.get_site_runtime(slug), capability)}

    def has_capability(self, site_name: str, capability: str) -> bool:
        slug = str(site_name or '').strip().lower()
        if slug not in _SITE_DEFINITIONS:
            return False
        return hasattr(self.get_site_runtime(slug), capability)

    def build_site_catalog(self) -> dict[str, dict]:
        catalog: dict[str, dict] = {}
        for slug in _SITE_DEFINITIONS:
            runtime = self.get_site_runtime(slug)
            descriptor = runtime.site_descriptor()
            defaults = dict(descriptor.get('metadata') or {})
            item = catalog.setdefault(
                slug,
                {
                    'label': defaults.get('label') or slug,
                    'domains': [],
                    'aliases': [],
                    'enabled': True,
                    'features': [],
                },
            )
            item['label'] = defaults.get('label') or item.get('label') or slug
            if descriptor.get('test_url'):
                item['test_url'] = descriptor['test_url']
            for alias in [str(alias).strip().lower() for alias in defaults.get('aliases') or [] if alias]:
                if alias not in item['aliases']:
                    item['aliases'].append(alias)
            for key in ('http', 'proxy', 'login', 'rate_limit', 'cookie', 'metadata', 'icon_url'):
                value = defaults.get(key)
                if value is not None:
                    item[key] = value
            item['features'] = [c for c in _SITE_CAPABILITIES if hasattr(runtime, c)]
            for domain in descriptor.get('domains') or []:
                normalized = str(domain).strip().lower()
                if normalized and normalized not in item['domains']:
                    item['domains'].append(normalized)
        return catalog

    def find_site_by_domain(self, domain: str | None) -> str | None:
        if not domain:
            return None
        value = str(domain).split(':')[0].strip().lower()
        for slug, info in self.build_site_catalog().items():
            for configured_domain in info.get('domains') or []:
                configured = str(configured_domain).strip().lower()
                if value == configured or value.endswith(f'.{configured}'):
                    return slug
        return None


_site_registry = SiteRegistry()


def get_site_registry() -> SiteRegistry:
    return _site_registry
