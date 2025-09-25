from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Type, Dict


class IdExtractor(ABC):
    domain: Optional[str] = None

    def __init__(self, url: str):
        self.url = url

    @abstractmethod
    def extract_id(self) -> str:
        raise NotImplementedError


class IdExtractorRegistry:
    _items: Dict[str, Type[IdExtractor]] = {}

    @classmethod
    def register(cls, extractor_class: Type[IdExtractor]):
        domain = getattr(extractor_class, 'domain', None)
        if not domain:
            raise AttributeError("IdExtractor must define 'domain'")
        cls._items[domain] = extractor_class
        return extractor_class

    @classmethod
    def get_extractor(cls, domain: str) -> Optional[Type[IdExtractor]]:
        return cls._items.get(domain)

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        return list(cls._items.keys())


register_extractor = IdExtractorRegistry.register


