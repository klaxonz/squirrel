"""Unified registry manager for all plugin types.

This module provides a centralized RegistryManager that manages all plugin registries
in a single place, making it easier to reset, query, and manage plugins across the system.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PluginRegistry(Generic[T]):
    """Generic plugin registry with thread-safe operations.

    This registry can store both Protocol-compatible objects and traditional classes.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._plugins: Dict[str, Union[Type[T], T]] = {}
        self._domain_mapping: Dict[str, str] = {}
        self._lock = threading.RLock()

    def register(
        self,
        key: str,
        plugin: Union[Type[T], T],
        domains: Optional[List[str]] = None,
    ) -> None:
        """Register a plugin with an optional domain mapping."""
        with self._lock:
            if key in self._plugins:
                logger.debug(f"{self.name}: overriding plugin for key: {key}")

            self._plugins[key] = plugin

            if domains:
                for domain in domains:
                    self._domain_mapping[domain.lower()] = key

    def get(self, key: str) -> Optional[Union[Type[T], T]]:
        """Get a plugin by key."""
        with self._lock:
            return self._plugins.get(key)

    def get_by_domain(self, domain: str) -> Optional[str]:
        """Get plugin key by domain."""
        with self._lock:
            key = self._domain_mapping.get(domain.lower())
            if key:
                return key

            parts = domain.lower().split('.')
            for i in range(len(parts) - 1):
                current_domain = '.'.join(parts[i:])
                key = self._domain_mapping.get(current_domain)
                if key:
                    return key

            return None

    def get_by_url(self, url: str) -> Optional[str]:
        """Get plugin key by URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            domain = domain.split(':')[0]
            return self.get_by_domain(domain)
        except Exception:
            return None

    def get_all_keys(self) -> List[str]:
        """Get all registered plugin keys."""
        with self._lock:
            return list(self._plugins.keys())

    def get_all_domains(self) -> List[str]:
        """Get all registered domains."""
        with self._lock:
            return list(self._domain_mapping.keys())

    def unregister(self, key: str) -> None:
        """Unregister a plugin."""
        with self._lock:
            if key in self._plugins:
                del self._plugins[key]
                domains_to_remove = [
                    domain for domain, plugin_key in self._domain_mapping.items()
                    if plugin_key == key
                ]
                for domain in domains_to_remove:
                    del self._domain_mapping[domain]

    def clear(self) -> None:
        """Clear all registered plugins."""
        with self._lock:
            self._plugins.clear()
            self._domain_mapping.clear()


class ComponentFactory(Generic[T]):
    """Generic factory for creating component instances."""

    def __init__(self, registry: PluginRegistry[T], name: str):
        self.registry = registry
        self.name = name
        self._instances: Dict[str, T] = {}
        self._lock = threading.RLock()

    def create(self, url: str) -> Optional[T]:
        """Create a component instance for the given URL."""
        key = self.registry.get_by_url(url)
        if not key:
            return None
        return self.get_by_key(key)

    def get_by_key(self, key: str) -> Optional[T]:
        """Get or create a component instance by key."""
        with self._lock:
            if key in self._instances:
                return self._instances[key]

            plugin = self.registry.get(key)
            if plugin is None:
                return None

            if isinstance(plugin, type):
                try:
                    instance = plugin()
                    self._instances[key] = instance
                    return instance
                except Exception as e:
                    logger.error(f"{self.name}: failed to instantiate {key}: {e}")
                    return None
            else:
                self._instances[key] = plugin
                return plugin

    def clear_cache(self) -> None:
        """Clear the instance cache."""
        with self._lock:
            self._instances.clear()


class RegistryManager:
    """Unified manager for all plugin registries.

    This class provides a single point of access to all plugin registries,
    making it easier to manage, reset, and query plugins across the system.
    """

    def __init__(self):
        self._lock = threading.RLock()

        self.extractor: PluginRegistry = PluginRegistry("extractor")
        self.subscription: PluginRegistry = PluginRegistry("subscription")
        self.importer: PluginRegistry = PluginRegistry("importer")
        self.login_checker: PluginRegistry = PluginRegistry("login_checker")
        self.handler: PluginRegistry = PluginRegistry("handler")
        self.mpd: PluginRegistry = PluginRegistry("mpd")
        self.subtitles: PluginRegistry = PluginRegistry("subtitles")
        self.id_extractor: PluginRegistry = PluginRegistry("id_extractor")
        self.downloader: PluginRegistry = PluginRegistry("downloader")
        self.proxy: PluginRegistry = PluginRegistry("proxy")
        self.proxy_config: PluginRegistry = PluginRegistry("proxy_config")

        self._extractor_factory: Optional[ComponentFactory] = None
        self._downloader_factory: Optional[ComponentFactory] = None

    def _all_registries(self) -> List[PluginRegistry]:
        """Get all registries as a list."""
        return [
            self.extractor,
            self.subscription,
            self.importer,
            self.login_checker,
            self.handler,
            self.mpd,
            self.subtitles,
            self.id_extractor,
            self.downloader,
            self.proxy,
            self.proxy_config,
        ]

    def reset_all(self) -> None:
        """Reset all registries and clear all caches."""
        with self._lock:
            for registry in self._all_registries():
                registry.clear()

            if self._extractor_factory:
                self._extractor_factory.clear_cache()
            if self._downloader_factory:
                self._downloader_factory.clear_cache()

            logger.info("All registries have been reset")

    def get_extractor_factory(self) -> ComponentFactory:
        """Get the extractor factory."""
        with self._lock:
            if self._extractor_factory is None:
                self._extractor_factory = ComponentFactory(self.extractor, "ExtractorFactory")
            return self._extractor_factory

    def get_downloader_factory(self) -> ComponentFactory:
        """Get the downloader factory."""
        with self._lock:
            if self._downloader_factory is None:
                self._downloader_factory = ComponentFactory(self.downloader, "DownloaderFactory")
            return self._downloader_factory

    def get_all_for_site(self, site_name: str) -> Dict[str, Any]:
        """Get all registered components for a specific site."""
        result = {}

        if self.extractor.get(site_name):
            result['extractor'] = self.extractor.get(site_name)
        if self.subscription.get(site_name):
            result['subscription'] = self.subscription.get(site_name)
        if self.importer.get(site_name):
            result['importer'] = self.importer.get(site_name)
        if self.login_checker.get(site_name):
            result['login_checker'] = self.login_checker.get(site_name)
        if self.handler.get(site_name):
            result['handler'] = self.handler.get(site_name)
        if self.mpd.get(site_name):
            result['mpd'] = self.mpd.get(site_name)
        if self.subtitles.get(site_name):
            result['subtitles'] = self.subtitles.get(site_name)
        if self.id_extractor.get(site_name):
            result['id_extractor'] = self.id_extractor.get(site_name)
        if self.downloader.get(site_name):
            result['downloader'] = self.downloader.get(site_name)
        if self.proxy.get(site_name):
            result['proxy'] = self.proxy.get(site_name)
        if self.proxy_config.get(site_name):
            result['proxy_config'] = self.proxy_config.get(site_name)

        return result

    def get_all_sites(self) -> List[str]:
        """Get all registered site names (from extractor registry)."""
        return self.extractor.get_all_keys()


_manager: Optional[RegistryManager] = None
_manager_lock = threading.Lock()


def get_registry_manager() -> RegistryManager:
    """Get the global registry manager singleton."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = RegistryManager()
    return _manager


def reset_registry_manager() -> None:
    """Reset the global registry manager."""
    global _manager
    with _manager_lock:
        if _manager is not None:
            _manager.reset_all()
        _manager = None
