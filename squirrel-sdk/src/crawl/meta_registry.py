from __future__ import annotations

from typing import Dict, Optional, Type

from .meta_origin import Video


class MetaRegistry:
    """Registry mapping domain -> Video subclass."""

    _items: Dict[str, Type[Video]] = {}

    @classmethod
    def register(cls, item_class: Type[Video]):
        domain = getattr(item_class, 'domain', None)
        if not domain:
            raise AttributeError("Video class must define 'domain' class attribute")
        cls._items[domain] = item_class
        return item_class

    @classmethod
    def get_meta_class(cls, domain: str) -> Optional[Type[Video]]:
        return cls._items.get(domain)

    @classmethod
    def get_all_meta_classes(cls) -> Dict[str, Type[Video]]:
        return dict(cls._items)

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        return list(cls._items.keys())


register_meta = MetaRegistry.register


class VideoFactory:
    @staticmethod
    def create_video(url: str, video_info) -> Video:
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split('.')

        for i in range(len(domain_parts) - 1):
            current_domain = '.'.join(domain_parts[i:])
            meta_class = MetaRegistry.get_meta_class(current_domain)
            if meta_class:
                return meta_class(url, video_info)
        raise ValueError(f"No meta class found for url {url}")


