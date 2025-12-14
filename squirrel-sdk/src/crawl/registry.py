"""Unified plugin registry system for Squirrel SDK.

This module provides the only registry system for all plugin types.
All plugins use Protocol-based interfaces.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, Union
from urllib.parse import urlparse

from .core import (
    Extractor,
    Subscription,
    UserSubscriptionImporter,
    LoginStatusResult,
)

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
                raise ValueError(f"{self.name}: Plugin already registered for key: {key}")
            
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
            # Try exact match first
            key = self._domain_mapping.get(domain.lower())
            if key:
                return key
            
            # Try subdomain matching (most specific to least specific)
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
            # Remove port if present
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
                # Remove domain mappings
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


# Global registries
_extractor_registry: Optional[PluginRegistry[Extractor]] = None
_subscription_registry: Optional[PluginRegistry[Subscription]] = None
_importer_registry: Optional[PluginRegistry[UserSubscriptionImporter]] = None
_login_checker_registry: Optional[PluginRegistry[Callable[[], LoginStatusResult]]] = None


def get_extractor_registry() -> PluginRegistry[Extractor]:
    """Get the global extractor registry."""
    global _extractor_registry
    if _extractor_registry is None:
        _extractor_registry = PluginRegistry[Extractor]("ExtractorRegistry")
    return _extractor_registry


def get_subscription_registry() -> PluginRegistry[Subscription]:
    """Get the global subscription registry."""
    global _subscription_registry
    if _subscription_registry is None:
        _subscription_registry = PluginRegistry[Subscription]("SubscriptionRegistry")
    return _subscription_registry


def get_importer_registry() -> PluginRegistry[UserSubscriptionImporter]:
    """Get the global user subscription importer registry."""
    global _importer_registry
    if _importer_registry is None:
        _importer_registry = PluginRegistry[UserSubscriptionImporter]("ImporterRegistry")
    return _importer_registry


def get_login_checker_registry() -> PluginRegistry[Callable[[], LoginStatusResult]]:
    """Get the global login checker registry."""
    global _login_checker_registry
    if _login_checker_registry is None:
        _login_checker_registry = PluginRegistry[Callable[[], LoginStatusResult]]("LoginCheckerRegistry")
    return _login_checker_registry


def reset_all_registries() -> None:
    """Reset all global registries (useful for testing).
    
    This resets all registries defined in this module. For other plugin type
    registries, use their respective reset functions or clear() methods.
    """
    import logging
    
    global _extractor_registry, _subscription_registry, _importer_registry, _login_checker_registry
    _extractor_registry = None
    _subscription_registry = None
    _importer_registry = None
    _login_checker_registry = None
    
    logger = logging.getLogger(__name__)
    
    # Reset other registries by importing and clearing them
    # These imports should not fail in normal operation, but we catch
    # ImportError/AttributeError to handle edge cases (e.g., during module reload)
    registries_to_reset = [
        (".url_handler", "get_handler_registry", "url_handler"),
        (".id_extractor", "get_id_extractor_registry", "id_extractor"),
        (".downloader", "get_downloader_registry", "downloader"),
        (".mpd", "get_mpd_registry", "mpd"),
        (".subtitles", "get_subtitles_registry", "subtitles"),
    ]
    
    for module_name, func_name, registry_name in registries_to_reset:
        try:
            module = __import__(module_name, fromlist=[func_name], level=1)
            get_registry = getattr(module, func_name)
            get_registry().clear()
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not reset {registry_name} registry: {e}")
    
    # Handle proxy registries separately (has two registries)
    try:
        from .proxy import get_proxy_registry, get_proxy_config_registry
        get_proxy_registry().clear()
        get_proxy_config_registry().clear()
    except (ImportError, AttributeError) as e:
        logger.debug(f"Could not reset proxy registries: {e}")


# Factory functions
class ExtractorFactory:
    """Factory for creating extractor instances."""
    
    def __init__(self, registry: PluginRegistry[Extractor]):
        self.registry = registry
        self._instances: Dict[str, Extractor] = {}
        self._lock = threading.RLock()
    
    def create(self, url: str) -> Optional[Extractor]:
        """Create an extractor instance for the given URL."""
        key = self.registry.get_by_url(url)
        if not key:
            return None
        return self.get_by_key(key)
    
    def get_by_key(self, key: str) -> Optional[Extractor]:
        """Get or create an extractor instance by key."""
        with self._lock:
            if key in self._instances:
                return self._instances[key]
            
            plugin = self.registry.get(key)
            if plugin is None:
                return None
            
            # If it's a class, instantiate it
            if isinstance(plugin, type):
                try:
                    instance = plugin()  # type: ignore[call-arg]
                    self._instances[key] = instance
                    return instance
                except Exception:
                    return None
            else:
                # It's already an instance
                self._instances[key] = plugin
                return plugin
    
    def clear_cache(self) -> None:
        """Clear the instance cache."""
        with self._lock:
            self._instances.clear()


_extractor_factory: Optional[ExtractorFactory] = None


def get_extractor_factory() -> ExtractorFactory:
    """Get the global extractor factory."""
    global _extractor_factory
    if _extractor_factory is None:
        _extractor_factory = ExtractorFactory(get_extractor_registry())
    return _extractor_factory


# Convenience decorators
def register_extractor(site_name: str, domains: List[str]):
    """Decorator to register an extractor plugin.
    
    Usage:
        @register_extractor("youtube", ["youtube.com", "youtu.be"])
        class MyExtractor:
            site_name = "youtube"
            supported_domains = ["youtube.com", "youtu.be"]
            ...
    """
    def decorator(cls_or_instance: Union[Type[Extractor], Extractor]):
        registry = get_extractor_registry()
        registry.register(site_name, cls_or_instance, domains)
        return cls_or_instance
    return decorator


def register_subscription(site_name: str, domains: List[str]):
    """Decorator to register a subscription plugin."""
    def decorator(cls: Type[Subscription]):
        registry = get_subscription_registry()
        registry.register(site_name, cls, domains)
        return cls
    return decorator


def register_user_subscription_importer(site_name: str):
    """Decorator to register a user subscription importer."""
    def decorator(cls_or_func: Union[Type[UserSubscriptionImporter], UserSubscriptionImporter]):
        registry = get_importer_registry()
        registry.register(site_name, cls_or_func)
        return cls_or_func
    return decorator


def register_login_checker(site_name: str):
    """Decorator to register a login status checker."""
    def decorator(func: Callable[[], LoginStatusResult]):
        registry = get_login_checker_registry()
        registry.register(site_name, func)
        return func
    return decorator

