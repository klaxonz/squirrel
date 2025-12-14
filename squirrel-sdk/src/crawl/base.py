"""Convenience base classes for writing crawl plugins.

Usage::

    from crawl import BaseExtractor

    class MyExtractor(BaseExtractor):
        site_name = "mytube"
        supported_domains = ["mytube.com", "mytu.be"]

        def can_handle(self, url: str) -> bool:
            return "mytube" in url

        def extract(self, task: ExtractionTask) -> ExtractionResult:
            ...

Importing the module that contains an extractor subclass will automatically
register it with the extractor registry.

Note: New code can also use the Extractor Protocol directly without
inheriting from BaseExtractor.
"""
from __future__ import annotations

import abc
from typing import List
from .core import ExtractionTask, ExtractionResult, Extractor
from .registry import register_extractor

__all__ = [
    "BaseExtractor",
]


class _ExtractorMeta(abc.ABCMeta):
    """Metaclass that auto-registers subclasses as extractor plugins."""

    def __new__(mcls, name, bases, namespace, **kwargs):  # noqa: D401
        cls = super().__new__(mcls, name, bases, namespace)
        # Skip abstract base itself
        if name != "BaseExtractor":
            site = getattr(cls, "site_name", None)
            domains: List[str] = getattr(cls, "supported_domains", [])
            if site and domains:
                register_extractor(site, domains)(cls)
        return cls


class BaseExtractor(metaclass=_ExtractorMeta):
    """Derive from this class to implement a concrete extractor plugin.
    
    This class provides a simple base for extractors. For more advanced
    functionality, consider using VideoExtractorBase or implementing the
    Extractor Protocol directly.
    
    Subclasses must:
    - Set site_name and supported_domains class attributes
    - Implement can_handle() and extract() methods
    """

    # Subclasses **must** override these two attributes
    site_name: str  # e.g. "youtube"
    supported_domains: List[str]

    # ---- Optional helpers -------------------------------------------------
    def validate_url(self, url: str) -> bool:  # noqa: D401
        """Basic validation: URL host matches any supported domain."""
        return any(f"://{d}" in url or d in url for d in self.supported_domains)

    # Subclasses must implement can_handle() and extract() methods
    # to satisfy the Extractor Protocol.
