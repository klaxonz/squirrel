from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable, Type
from urllib.parse import urlparse

from .registries import PluginRegistry, get_registry_manager


@runtime_checkable
class Downloader(Protocol):
    """Protocol for site-specific downloaders."""

    domains: List[str]
    url: str

    def get_video_info(self, queue_name: Optional[str] = None) -> Any:
        """Return metadata extracted from the video page/url."""
        ...

    def download(
        self,
        subscription: Any,
        video: Any,
        task: Any,
        queue_thread_name: str,
        video_info: Optional[Any] = None,
    ) -> Any:
        """Execute the download workflow and return the resulting task state."""
        ...


def get_downloader_registry() -> PluginRegistry[Type[Downloader]]:
    """Get the global downloader registry."""
    return get_registry_manager().downloader


class DownloaderFactory:
    """Factory for creating downloader instances."""

    def __init__(self, registry: PluginRegistry[Type[Downloader]]):
        self.registry = registry

    def create_downloader(self, url: str) -> Downloader:
        """Create a downloader instance for the given URL."""
        if not url or not isinstance(url, str):
            raise ValueError("A valid URL string must be provided.")

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower().split(':')[0]

        key = self.registry.get_by_domain(domain)
        if not key:
            supported = self.registry.get_all_domains()
            raise ValueError(
                f"No downloader registered for domain '{parsed_url.netloc}'. "
                f"Supported domains: {supported if supported else '(none)'}"
            )

        downloader_cls = self.registry.get(key)
        if not downloader_cls or not isinstance(downloader_cls, type):
            raise ValueError(f"Downloader class for key '{key}' is invalid or not a class.")

        return downloader_cls(url)


def get_downloader_factory() -> DownloaderFactory:
    """Get the global downloader factory."""
    return DownloaderFactory(get_downloader_registry())


def register_downloader(downloader_cls: Type[Downloader]) -> Type[Downloader]:
    """Decorator to register a downloader.
    
    The downloader class must define a `domains` attribute (list of strings).
    The first domain in the list will be used as the registry key.
    
    Usage:
        @register_downloader
        class MyDownloader:
            domains = ["example.com", "www.example.com"]
            
            def __init__(self, url: str):
                self.url = url
                self.domain = self.domains[0]
            ...
    """
    domains = getattr(downloader_cls, "domains", None)
    
    if not domains:
        raise AttributeError(
            f"Downloader class '{downloader_cls.__name__}' must define 'domains' attribute "
            f"(list of supported domain strings)"
        )
    
    if not isinstance(domains, list) or not domains:
        raise ValueError(
            f"Downloader class '{downloader_cls.__name__}': 'domains' must be a non-empty list"
        )
    
    if not all(isinstance(d, str) and d for d in domains):
        raise ValueError(
            f"Downloader class '{downloader_cls.__name__}': all items in 'domains' must be non-empty strings"
        )
    
    key = domains[0]
    registry = get_downloader_registry()
    registry.register(key, downloader_cls, domains)
    
    return downloader_cls

