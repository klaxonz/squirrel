from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Type, Dict


class BaseSubtitlesProvider(ABC):
    domain: Optional[str] = None

    @abstractmethod
    def get_subtitles(self, video, lang: str, fmt: str = "srt") -> Tuple[str, str]:
        raise NotImplementedError


class SubtitlesRegistry:
    _items: Dict[str, Type[BaseSubtitlesProvider]] = {}

    @classmethod
    def register(cls, provider_class: Type[BaseSubtitlesProvider]):
        domain = getattr(provider_class, 'domain', None)
        if not domain:
            raise AttributeError("Subtitles provider must define 'domain'")
        cls._items[domain] = provider_class
        return provider_class

    @classmethod
    def get_provider_class(cls, domain: str) -> Optional[Type[BaseSubtitlesProvider]]:
        return cls._items.get(domain)

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        return list(cls._items.keys())


register_subtitles = SubtitlesRegistry.register


