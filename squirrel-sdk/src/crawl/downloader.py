from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, Type, Union
from urllib.parse import urlparse

from .registry import PluginRegistry


@runtime_checkable
class Downloader(Protocol):
    """Protocol for site-specific downloaders."""
    
    domain: Optional[str]
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


# Global registry
_downloader_registry: Optional[PluginRegistry[Type[Downloader]]] = None


def get_downloader_registry() -> PluginRegistry[Type[Downloader]]:
    """Get the global downloader registry."""
    global _downloader_registry
    if _downloader_registry is None:
        _downloader_registry = PluginRegistry[Type[Downloader]]("DownloaderRegistry")
    return _downloader_registry


class DownloaderFactory:
    """Factory for creating downloader instances."""
    
    def __init__(self, registry: PluginRegistry[Type[Downloader]]):
        self.registry = registry
    
    def create_downloader(self, url: str) -> Downloader:
        """Create a downloader instance for the given URL."""
        if not isinstance(url, str) or not url:
            raise ValueError("A valid URL string must be provided.")
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        # Remove port if present
        domain = domain.split(':')[0]
        
        # Try to find downloader by domain
        key = self.registry.get_by_domain(domain)
        if key:
            downloader_cls = self.registry.get(key)
            if downloader_cls and isinstance(downloader_cls, type):
                return downloader_cls(url)  # type: ignore[call-arg]
        
        supported = self.registry.get_all_domains()
        raise ValueError(
            f"No downloader registered for domain '{parsed_url.netloc}' or its parent domains. "
            f"Supported domains are: {supported}"
        )


_factory_singleton: Optional[DownloaderFactory] = None


def get_downloader_factory() -> DownloaderFactory:
    """Get the global downloader factory."""
    global _factory_singleton
    if _factory_singleton is None:
        _factory_singleton = DownloaderFactory(get_downloader_registry())
    return _factory_singleton


def register_downloader(domains: Optional[Union[str, List[str]]] = None):
    """Decorator to register a downloader.
    
    Usage:
        # Method 1: Auto-detect domain from class attribute
        @register_downloader
        class MyDownloader:
            domain = "example.com"
            ...
        
        # Method 2: Explicitly specify domain(s)
        @register_downloader("example.com")
        class MyDownloader:
            domain = "example.com"
            ...
        
        @register_downloader(["example.com", "www.example.com"])
        class MyDownloader:
            domain = "example.com"
            ...
    """
    if domains is None:
        # Used as @register_downloader (no parentheses)
        def decorator(downloader_cls: Type[Downloader]):
            domain_attr = getattr(downloader_cls, "domain", None)
            if not domain_attr:
                # Try to get from domains attribute
                domains_attr = getattr(downloader_cls, "domains", None)
                if domains_attr and isinstance(domains_attr, list) and domains_attr:
                    domain_attr = domains_attr[0]
                else:
                    raise AttributeError("Downloader class must define 'domain' or 'domains' attribute")
            
            domains_list = [domain_attr]
            # Also check if there's a domains attribute
            domains_attr = getattr(downloader_cls, "domains", None)
            if domains_attr and isinstance(domains_attr, list):
                domains_list = domains_attr
            
            registry = get_downloader_registry()
            registry.register(domain_attr, downloader_cls, domains_list)
            return downloader_cls
        return decorator
    else:
        # Used as @register_downloader("domain") or @register_downloader(["domain1", "domain2"])
        if isinstance(domains, str):
            domains = [domains]
        
        def decorator(downloader_cls: Type[Downloader]):
            registry = get_downloader_registry()
            # Use first domain as key, or use class domain attribute
            domain_attr = getattr(downloader_cls, "domain", None)
            if isinstance(domain_attr, str):
                key = domain_attr
            else:
                key = domains[0] if domains else downloader_cls.__name__
            
            registry.register(key, downloader_cls, domains)
            return downloader_cls
        return decorator

