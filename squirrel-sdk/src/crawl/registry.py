"""Unified plugin registry system for Squirrel SDK.

This module provides the registry system for all plugin types.
All plugins use Protocol-based interfaces.

The actual registry instances are managed by RegistryManager in registries.py.
This module provides convenience functions for backward compatibility.
"""
from __future__ import annotations

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


def get_extractor_registry() -> PluginRegistry[Extractor]:
    """Get the global extractor registry."""
    return get_registry_manager().extractor


def get_subscription_registry() -> PluginRegistry[Subscription]:
    """Get the global subscription registry."""
    return get_registry_manager().subscription


def get_importer_registry() -> PluginRegistry[UserSubscriptionImporter]:
    """Get the global user subscription importer registry."""
    return get_registry_manager().importer


def get_login_checker_registry() -> PluginRegistry[Callable[[], LoginStatusResult]]:
    """Get the global login checker registry."""
    return get_registry_manager().login_checker


def reset_all_registries() -> None:
    """Reset all global registries."""
    reset_registry_manager()


ExtractorFactory = ComponentFactory


def get_extractor_factory() -> ComponentFactory:
    """Get the global extractor factory."""
    return get_registry_manager().get_extractor_factory()


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

