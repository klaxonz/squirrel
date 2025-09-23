"""Convenience base classes for writing crawl plugins.

Usage::

    from squirrel_sdk.crawl.plugin_base import BaseExtractor

    class MyExtractor(BaseExtractor):
        site_name = "mytube"
        supported_domains = ["mytube.com", "mytu.be"]

        def can_handle(self, url: str) -> bool:
            return "mytube" in url

        def extract(self, task: ExtractionTask) -> ExtractionResult:
            ...

Importing the module that contains an extractor subclass will automatically
register it with :pymeth:`squirrel_sdk.crawl.registry.register_extractor`.
"""
from __future__ import annotations

import abc
from typing import List

from .interfaces import ExtractionResult, ExtractionTask, IExtractor
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


class BaseExtractor(IExtractor, metaclass=_ExtractorMeta):
    """Derive from this class to implement a concrete extractor plugin."""

    # Subclasses **must** override these two attributes
    site_name: str  # e.g. "youtube"
    supported_domains: List[str]

    # ---- Optional helpers -------------------------------------------------
    def validate_url(self, url: str) -> bool:  # noqa: D401
        """Basic validation: URL host matches any supported domain."""
        return any(f"://{d}" in url for d in self.supported_domains)

    # Subclasses still need to implement can_handle & extract (inherited
    # as abstract from IExtractor).
