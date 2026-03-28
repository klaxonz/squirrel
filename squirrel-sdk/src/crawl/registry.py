"""Unified plugin registry system for Squirrel SDK.

This module provides the registry system for all plugin types.
All plugins use Protocol-based interfaces.

The actual registry instances are managed by RegistryManager in registries.py.
This module provides convenience functions for backward compatibility only.
"""
from __future__ import annotations

import warnings
from typing import Callable, List, Type, Union

from .core import (
    Extractor,
    Subscription,
    UserSubscriptionImporter,
    LoginStatusResult,
)
from .registries import (
    PluginRegistry,
    ComponentFactory,
    get_registry_manager,
    reset_registry_manager,
)


class LegacyRegistryApiWarning(DeprecationWarning):
    """Warning emitted when a legacy in-process registry API is used."""


warnings.simplefilter('default', LegacyRegistryApiWarning)


def _warn_legacy_api(api_name: str) -> None:
    warnings.warn(
        (
            f'{api_name} is a legacy in-process registry API. '
            'Prefer runtime V2 manifests and create_plugin_runtime() for new plugins.'
        ),
        LegacyRegistryApiWarning,
        stacklevel=2,
    )


def get_extractor_registry() -> PluginRegistry[Extractor]:
    """Get the legacy global extractor registry."""
    _warn_legacy_api('get_extractor_registry()')
    return get_registry_manager().extractor


def get_subscription_registry() -> PluginRegistry[Subscription]:
    """Get the legacy global subscription registry."""
    _warn_legacy_api('get_subscription_registry()')
    return get_registry_manager().subscription


def get_importer_registry() -> PluginRegistry[UserSubscriptionImporter]:
    """Get the legacy global user subscription importer registry."""
    _warn_legacy_api('get_importer_registry()')
    return get_registry_manager().importer


def get_login_checker_registry() -> PluginRegistry[Callable[[], LoginStatusResult]]:
    """Get the legacy global login checker registry."""
    _warn_legacy_api('get_login_checker_registry()')
    return get_registry_manager().login_checker


def reset_all_registries() -> None:
    """Reset all legacy global registries."""
    _warn_legacy_api('reset_all_registries()')
    reset_registry_manager()


ExtractorFactory = ComponentFactory


def get_extractor_factory() -> ComponentFactory:
    """Get the legacy global extractor factory."""
    _warn_legacy_api('get_extractor_factory()')
    return get_registry_manager().get_extractor_factory()


# Convenience decorators
def register_extractor(site_name: str, domains: List[str]):
    """Legacy decorator to register an extractor plugin in-process.
    
    Usage:
        @register_extractor("youtube", ["youtube.com", "youtu.be"])
        class MyExtractor:
            site_name = "youtube"
            supported_domains = ["youtube.com", "youtu.be"]
            ...
    """
    def decorator(cls_or_instance: Union[Type[Extractor], Extractor]):
        _warn_legacy_api('register_extractor()')
        registry = get_extractor_registry()
        registry.register(site_name, cls_or_instance, domains)
        return cls_or_instance
    return decorator


def register_subscription(site_name: str, domains: List[str]):
    """Legacy decorator to register a subscription plugin in-process."""
    def decorator(cls: Type[Subscription]):
        _warn_legacy_api('register_subscription()')
        registry = get_subscription_registry()
        registry.register(site_name, cls, domains)
        return cls
    return decorator


def register_user_subscription_importer(site_name: str):
    """Legacy decorator to register a user subscription importer in-process."""
    def decorator(cls_or_func: Union[Type[UserSubscriptionImporter], UserSubscriptionImporter]):
        _warn_legacy_api('register_user_subscription_importer()')
        registry = get_importer_registry()
        registry.register(site_name, cls_or_func)
        return cls_or_func
    return decorator


def register_login_checker(site_name: str):
    """Legacy decorator to register a login status checker in-process."""
    def decorator(func: Callable[[], LoginStatusResult]):
        _warn_legacy_api('register_login_checker()')
        registry = get_login_checker_registry()
        registry.register(site_name, func)
        return func
    return decorator

