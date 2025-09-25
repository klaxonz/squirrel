from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Type, Dict


class VideoUrlHandler(ABC):
    domain: Optional[str] = None

    @abstractmethod
    def get_video_url(self, video) -> dict:
        """Return a serializable dict for VideoUrlDto construction by backend."""
        raise NotImplementedError


class HandlerRegistry:
    _items: Dict[str, Type[VideoUrlHandler]] = {}

    @classmethod
    def register(cls, handler_class: Type[VideoUrlHandler]):
        domain = getattr(handler_class, 'domain', None)
        if not domain:
            raise AttributeError("Handler class must define 'domain'")
        cls._items[domain] = handler_class
        return handler_class

    @classmethod
    def get_handler(cls, domain: str) -> Optional[Type[VideoUrlHandler]]:
        return cls._items.get(domain)

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        return list(cls._items.keys())


register_handler = HandlerRegistry.register


