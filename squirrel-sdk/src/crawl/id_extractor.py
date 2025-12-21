from __future__ import annotations

import re
from typing import List, Optional, Protocol, runtime_checkable

from .registries import PluginRegistry, get_registry_manager


@runtime_checkable
class IdExtractor(Protocol):
    """Protocol for ID extractors.

    Extractors extract video/channel IDs from URLs.
    """

    domains: List[str]
    url: str

    def extract_id(self) -> str:
        """Extract the ID from the URL."""
        ...


class RegexIdExtractor:
    """Base class for regex-based ID extractors.

    Subclasses only need to define `domains` (or `domain`) and `pattern`:

        @register_id_extractor
        class PornhubIdExtractor(RegexIdExtractor):
            domains = ['pornhub.com']
            pattern = r"viewkey=([^&]+)"

    For more complex patterns, override `group_index` (default 1) or
    implement `extract_id()` directly.
    """

    domains: List[str] = []
    domain: Optional[str] = None
    pattern: Optional[str] = None
    group_index: int = 1

    def __init__(self, url: str):
        self.url = url

    def extract_id(self) -> str:
        if not self.pattern:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'pattern' attribute"
            )
        match = re.search(self.pattern, self.url)
        if match:
            return match.group(self.group_index)
        raise ValueError(f"Cannot extract ID from URL: {self.url}")


def get_id_extractor_registry() -> PluginRegistry[IdExtractor]:
    """Get the global ID extractor registry."""
    return get_registry_manager().id_extractor


def register_id_extractor(domains_or_cls=None):
    """Decorator to register an ID extractor.

    Usage:
        # Method 1: Auto-detect domains from class attribute
        @register_id_extractor
        class MyIdExtractor:
            domains = ["example.com"]
            ...

        # Method 2: Explicitly specify domains
        @register_id_extractor(["example.com"])
        class MyIdExtractor:
            domains = ["example.com"]
            ...
    """
    def decorator(cls_or_instance: IdExtractor):
        if isinstance(domains_or_cls, list):
            domains = domains_or_cls
        else:
            domains = getattr(cls_or_instance, 'domains', None)
            if not domains:
                domain = getattr(cls_or_instance, 'domain', None)
                domains = [domain] if domain else None

        if not domains:
            raise AttributeError("IdExtractor must define 'domains' attribute")

        registry = get_id_extractor_registry()
        key = domains[0]
        registry.register(key, cls_or_instance, domains)
        return cls_or_instance

    if domains_or_cls is not None and not isinstance(domains_or_cls, list):
        return decorator(domains_or_cls)

    return decorator

