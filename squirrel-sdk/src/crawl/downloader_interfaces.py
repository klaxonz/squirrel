from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional, Type
from urllib.parse import urlparse


class BaseDownloader(ABC):
    """Abstract base class for site-specific downloaders."""

    domain: Optional[str] = None

    def __init__(self, url: str) -> None:
        self.url = url

    @abstractmethod
    def get_video_info(self, queue_name: Optional[str] = None):
        """Return metadata extracted from the video page/url."""

    @abstractmethod
    def download(
        self,
        subscription,
        video,
        task,
        queue_thread_name: str,
        video_info=None,
    ):
        """Execute the download workflow and return the resulting task state."""


class DownloaderRegistry:
    _items: Dict[str, Type[BaseDownloader]] = {}

    @classmethod
    def register(cls, downloader_cls: Type[BaseDownloader]):
        domains = []
        domain_attr = getattr(downloader_cls, "domain", None)
        if isinstance(domain_attr, str):
            domains.append(domain_attr)
        else:
            domains.extend(getattr(downloader_cls, "domains", []) or [])

        if not domains:
            raise AttributeError("Downloader class must define 'domain' or 'domains'")

        for d in domains:
            cls._items[d] = downloader_cls
        return downloader_cls

    @classmethod
    def get_downloader_class(cls, domain: str) -> Optional[Type[BaseDownloader]]:
        return cls._items.get(domain)

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        return list(cls._items.keys())


class DownloaderFactory:
    def __init__(self, registry: DownloaderRegistry):
        self.registry = registry

    def create_downloader(self, url: str) -> BaseDownloader:
        if not isinstance(url, str) or not url:
            raise ValueError("A valid URL string must be provided.")

        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split('.')

        for i in range(len(domain_parts) - 1):
            current_domain = '.'.join(domain_parts[i:])
            downloader_cls = self.registry.get_downloader_class(current_domain)
            if downloader_cls:
                return downloader_cls(url)

        supported = self.registry.get_supported_domains()
        raise ValueError(
            f"No downloader registered for domain '{parsed_url.netloc}' or its parent domains. "
            f"Supported domains are: {supported}"
        )


_registry_singleton: Optional[DownloaderRegistry] = None
_factory_singleton: Optional[DownloaderFactory] = None


def get_downloader_registry() -> DownloaderRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = DownloaderRegistry()
    return _registry_singleton


def get_downloader_factory() -> DownloaderFactory:
    global _factory_singleton
    if _factory_singleton is None:
        _factory_singleton = DownloaderFactory(get_downloader_registry())
    return _factory_singleton


def register_downloader(cls: Type[BaseDownloader]):
    return get_downloader_registry().register(cls)



