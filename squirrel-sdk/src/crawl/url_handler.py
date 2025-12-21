from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .registries import PluginRegistry, get_registry_manager


@runtime_checkable
class VideoUrlHandler(Protocol):
    """Protocol for video URL handlers.

    Handlers convert video objects into serializable dictionaries for VideoUrlDto construction.
    """

    domains: List[str]

    def get_video_url(self, video: Any) -> Dict[str, Any]:
        """Return a serializable dict for VideoUrlDto construction by backend."""
        ...


def get_handler_registry() -> PluginRegistry[VideoUrlHandler]:
    """Get the global handler registry."""
    return get_registry_manager().handler


def register_handler(domains_or_cls=None):
    """Decorator to register a video URL handler.

    Usage:
        # Method 1: Auto-detect domains from class attribute
        @register_handler
        class MyHandler:
            domains = ["example.com"]
            ...

        # Method 2: Explicitly specify domains
        @register_handler(["example.com"])
        class MyHandler:
            domains = ["example.com"]
            ...
    """
    def decorator(cls_or_instance: VideoUrlHandler):
        if isinstance(domains_or_cls, list):
            domains = domains_or_cls
        else:
            domains = getattr(cls_or_instance, 'domains', None)
            if domains is None:
                domain = getattr(cls_or_instance, 'domain', None)
                domains = [domain] if domain else None

        if not domains:
            raise AttributeError("Handler class must define 'domains' attribute")

        registry = get_handler_registry()
        key = domains[0]
        registry.register(key, cls_or_instance, domains)
        return cls_or_instance

    if domains_or_cls is not None and not isinstance(domains_or_cls, list):
        return decorator(domains_or_cls)

    return decorator

