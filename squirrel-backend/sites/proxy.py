from fastapi import Request

from sites.video_proxy import VideoProxy
from sites.proxy_registry import ProxyRegistry


class ProxyFactory:
    @staticmethod
    def create_proxy(domain: str, request: Request) -> VideoProxy:
        proxy_class = ProxyRegistry.get_proxy_class(domain)
        if proxy_class:
            return proxy_class(request)

        # Fallback to a generic proxy if no specific one is registered
        # This requires the generic proxy to handle the domain dynamically.
        # For now, we raise an error if no specific proxy is found.
        raise ValueError(f"No proxy registered for domain: {domain}")

