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


def register_mpd(domain: Optional[str] = None):
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
    if domain is None:
        # Used as @register_mpd (no parentheses)
        def decorator(builder_class: Type[MpdBuilder]):
            domain_attr = getattr(builder_class, 'domain', None)
            if not domain_attr:
                raise AttributeError("MPD builder must define 'domain' attribute")
            registry = get_mpd_registry()
            registry.register(domain_attr, builder_class, [domain_attr])
            return builder_class
        return decorator
    else:
        # Used as @register_mpd("domain")
        def decorator(builder_class: Type[MpdBuilder]):
            registry = get_mpd_registry()
            registry.register(domain, builder_class, [domain])
            return builder_class
        return decorator

