from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable, Type

from .registries import PluginRegistry, get_registry_manager


@runtime_checkable
class MpdBuilder(Protocol):
    """Protocol for MPD (Media Presentation Description) builders."""

    domains: List[str]

    def build_mpd(self, video: Any) -> str:
        """Build MPD content for the given video."""
        ...


def get_mpd_registry() -> PluginRegistry[Type[MpdBuilder]]:
    """Get the global MPD builder registry."""
    return get_registry_manager().mpd


def register_mpd(domains_or_cls=None):
    """Decorator to register an MPD builder.

    Usage:
        # Method 1: Auto-detect domains from class attribute
        @register_mpd
        class MyMpdBuilder:
            domains = ["example.com"]
            ...

        # Method 2: Explicitly specify domains
        @register_mpd(["example.com"])
        class MyMpdBuilder:
            domains = ["example.com"]
            ...
    """
    def decorator(builder_class: Type[MpdBuilder]):
        if isinstance(domains_or_cls, list):
            domains = domains_or_cls
        else:
            domains = getattr(builder_class, 'domains', None)
            if not domains:
                domain = getattr(builder_class, 'domain', None)
                domains = [domain] if domain else None

        if not domains:
            raise AttributeError("MPD builder must define 'domains' attribute")

        registry = get_mpd_registry()
        key = domains[0]
        registry.register(key, builder_class, domains)
        return builder_class

    if domains_or_cls is not None and not isinstance(domains_or_cls, list):
        return decorator(domains_or_cls)

    return decorator

