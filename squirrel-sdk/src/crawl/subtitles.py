from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable, Tuple, Type

from .registry import PluginRegistry


@runtime_checkable
class SubtitlesProvider(Protocol):
    """Protocol for subtitles providers."""
    
    domain: Optional[str]
    
    def get_subtitles(self, video: Any, lang: str, fmt: str = "srt") -> Tuple[str, str]:
        """Get subtitles for the given video in the specified language and format.
        
        Returns:
            Tuple of (subtitle content, format)
        """
        ...


# Global registry
_subtitles_registry: Optional[PluginRegistry[Type[SubtitlesProvider]]] = None


def get_subtitles_registry() -> PluginRegistry[Type[SubtitlesProvider]]:
    """Get the global subtitles provider registry."""
    global _subtitles_registry
    if _subtitles_registry is None:
        _subtitles_registry = PluginRegistry[Type[SubtitlesProvider]]("SubtitlesRegistry")
    return _subtitles_registry


def register_subtitles(domain_or_cls=None):
    """Decorator to register a subtitles provider.

    Usage:
        # Method 1: Auto-detect domain from class attribute
        @register_subtitles
        class MySubtitlesProvider:
            domain = "example.com"
            ...

        # Method 2: Explicitly specify domain
        @register_subtitles("example.com")
        class MySubtitlesProvider:
            domain = "example.com"
            ...
    """
    def decorator(provider_class: Type[SubtitlesProvider]):
        if isinstance(domain_or_cls, str):
            domain_attr = domain_or_cls
        else:
            domain_attr = getattr(provider_class, 'domain', None)

        if not domain_attr:
            raise AttributeError("Subtitles provider must define 'domain' attribute")

        registry = get_subtitles_registry()
        registry.register(domain_attr, provider_class, [domain_attr])
        return provider_class

    # If called without parentheses, domain_or_cls is the class itself
    if domain_or_cls is not None and not isinstance(domain_or_cls, str):
        return decorator(domain_or_cls)

    # If called with parentheses (with or without domain argument)
    return decorator

