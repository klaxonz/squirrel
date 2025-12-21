from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable, Tuple, Type

from .registries import PluginRegistry, get_registry_manager


@runtime_checkable
class SubtitlesProvider(Protocol):
    """Protocol for subtitles providers."""

    domains: List[str]

    def get_subtitles(self, video: Any, lang: str, fmt: str = "srt") -> Tuple[str, str]:
        """Get subtitles for the given video in the specified language and format.

        Returns:
            Tuple of (subtitle content, format)
        """
        ...


def get_subtitles_registry() -> PluginRegistry[Type[SubtitlesProvider]]:
    """Get the global subtitles provider registry."""
    return get_registry_manager().subtitles


def register_subtitles(domains_or_cls=None):
    """Decorator to register a subtitles provider.

    Usage:
        # Method 1: Auto-detect domains from class attribute
        @register_subtitles
        class MySubtitlesProvider:
            domains = ["example.com"]
            ...

        # Method 2: Explicitly specify domains
        @register_subtitles(["example.com"])
        class MySubtitlesProvider:
            domains = ["example.com"]
            ...
    """
    def decorator(provider_class: Type[SubtitlesProvider]):
        if isinstance(domains_or_cls, list):
            domains = domains_or_cls
        else:
            domains = getattr(provider_class, 'domains', None)
            if not domains:
                domain = getattr(provider_class, 'domain', None)
                domains = [domain] if domain else None

        if not domains:
            raise AttributeError("Subtitles provider must define 'domains' attribute")

        registry = get_subtitles_registry()
        key = domains[0]
        registry.register(key, provider_class, domains)
        return provider_class

    if domains_or_cls is not None and not isinstance(domains_or_cls, list):
        return decorator(domains_or_cls)

    return decorator

