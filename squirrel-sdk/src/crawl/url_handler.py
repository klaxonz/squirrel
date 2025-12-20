from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .registry import PluginRegistry


@runtime_checkable
class VideoUrlHandler(Protocol):
    """Protocol for video URL handlers.
    
    Handlers convert video objects into serializable dictionaries for VideoUrlDto construction.
    """
    
    domain: Optional[str]
    
    def get_video_url(self, video: Any) -> Dict[str, Any]:
        """Return a serializable dict for VideoUrlDto construction by backend."""
        ...


# Global registry
_handler_registry: Optional[PluginRegistry[VideoUrlHandler]] = None


def get_handler_registry() -> PluginRegistry[VideoUrlHandler]:
    """Get the global handler registry."""
    global _handler_registry
    if _handler_registry is None:
        _handler_registry = PluginRegistry[VideoUrlHandler]("HandlerRegistry")
    return _handler_registry


def register_handler(domain_or_cls=None):
    """Decorator to register a video URL handler.

    Usage:
        # Method 1: Auto-detect domain from class attribute
        @register_handler
        class MyHandler:
            domain = "example.com"
            ...

        # Method 2: Explicitly specify domain
        @register_handler("example.com")
        class MyHandler:
            domain = "example.com"
            ...
    """
    def decorator(cls_or_instance: VideoUrlHandler):
        # Determine the domain: use explicit domain if string, otherwise get from class
        if isinstance(domain_or_cls, str):
            domain_attr = domain_or_cls
        else:
            domain_attr = getattr(cls_or_instance, 'domain', None)

        if not domain_attr:
            raise AttributeError("Handler class must define 'domain' attribute")

        registry = get_handler_registry()
        registry.register(domain_attr, cls_or_instance, [domain_attr])
        return cls_or_instance

    # If called without parentheses, domain_or_cls is the class itself
    if domain_or_cls is not None and not isinstance(domain_or_cls, str):
        return decorator(domain_or_cls)

    # If called with parentheses (with or without domain argument)
    return decorator

