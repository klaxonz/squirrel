from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable, Type

from .registry import PluginRegistry


@runtime_checkable
class MpdBuilder(Protocol):
    """Protocol for MPD (Media Presentation Description) builders."""
    
    domain: Optional[str]
    
    def build_mpd(self, video: Any) -> str:
        """Build MPD content for the given video."""
        ...


# Global registry
_mpd_registry: Optional[PluginRegistry[Type[MpdBuilder]]] = None


def get_mpd_registry() -> PluginRegistry[Type[MpdBuilder]]:
    """Get the global MPD builder registry."""
    global _mpd_registry
    if _mpd_registry is None:
        _mpd_registry = PluginRegistry[Type[MpdBuilder]]("MpdRegistry")
    return _mpd_registry


def register_mpd(domain_or_cls=None):
    """Decorator to register an MPD builder.

    Usage:
        # Method 1: Auto-detect domain from class attribute
        @register_mpd
        class MyMpdBuilder:
            domain = "example.com"
            ...

        # Method 2: Explicitly specify domain
        @register_mpd("example.com")
        class MyMpdBuilder:
            domain = "example.com"
            ...
    """
    def decorator(builder_class: Type[MpdBuilder]):
        if isinstance(domain_or_cls, str):
            domain_attr = domain_or_cls
        else:
            domain_attr = getattr(builder_class, 'domain', None)

        if not domain_attr:
            raise AttributeError("MPD builder must define 'domain' attribute")

        registry = get_mpd_registry()
        registry.register(domain_attr, builder_class, [domain_attr])
        return builder_class

    # If called without parentheses, domain_or_cls is the class itself
    if domain_or_cls is not None and not isinstance(domain_or_cls, str):
        return decorator(domain_or_cls)

    # If called with parentheses (with or without domain argument)
    return decorator

