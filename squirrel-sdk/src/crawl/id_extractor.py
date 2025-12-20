from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from .registry import PluginRegistry


@runtime_checkable
class IdExtractor(Protocol):
    """Protocol for ID extractors.
    
    Extractors extract video/channel IDs from URLs.
    """
    
    domain: Optional[str]
    url: str
    
    def extract_id(self) -> str:
        """Extract the ID from the URL."""
        ...


# Global registry
_id_extractor_registry: Optional[PluginRegistry[IdExtractor]] = None


def get_id_extractor_registry() -> PluginRegistry[IdExtractor]:
    """Get the global ID extractor registry."""
    global _id_extractor_registry
    if _id_extractor_registry is None:
        _id_extractor_registry = PluginRegistry[IdExtractor]("IdExtractorRegistry")
    return _id_extractor_registry


def register_id_extractor(domain_or_cls=None):
    """Decorator to register an ID extractor.

    Usage:
        # Method 1: Auto-detect domain from class attribute
        @register_id_extractor
        class MyIdExtractor:
            domain = "example.com"
            ...

        # Method 2: Explicitly specify domain
        @register_id_extractor("example.com")
        class MyIdExtractor:
            domain = "example.com"
            ...
    """
    def decorator(cls_or_instance: IdExtractor):
        if isinstance(domain_or_cls, str):
            domain_attr = domain_or_cls
        else:
            domain_attr = getattr(cls_or_instance, 'domain', None)

        if not domain_attr:
            raise AttributeError("IdExtractor must define 'domain' attribute")

        registry = get_id_extractor_registry()
        registry.register(domain_attr, cls_or_instance, [domain_attr])
        return cls_or_instance

    # If called without parentheses, domain_or_cls is the class itself
    if domain_or_cls is not None and not isinstance(domain_or_cls, str):
        return decorator(domain_or_cls)

    # If called with parentheses (with or without domain argument)
    return decorator

