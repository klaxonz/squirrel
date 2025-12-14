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


def register_id_extractor(domain: Optional[str] = None):
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
    # Support both @register_id_extractor and @register_id_extractor("domain")
    if domain is None:
        # Used as @register_id_extractor (no parentheses)
        def decorator(cls_or_instance: IdExtractor):
            domain_attr = getattr(cls_or_instance, 'domain', None)
            if not domain_attr:
                raise AttributeError("IdExtractor must define 'domain' attribute")
            registry = get_id_extractor_registry()
            registry.register(domain_attr, cls_or_instance, [domain_attr])
            return cls_or_instance
        return decorator
    else:
        # Used as @register_id_extractor("domain")
        def decorator(cls_or_instance: IdExtractor):
            registry = get_id_extractor_registry()
            registry.register(domain, cls_or_instance, [domain])
            return cls_or_instance
        return decorator

