from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Type, Dict


class BaseMpdBuilder(ABC):
    domain: Optional[str] = None

    @abstractmethod
    def build_mpd(self, video) -> str:
        raise NotImplementedError


class MpdRegistry:
    _items: Dict[str, Type[BaseMpdBuilder]] = {}

    @classmethod
    def register(cls, builder_class: Type[BaseMpdBuilder]):
        domain = getattr(builder_class, 'domain', None)
        if not domain:
            raise AttributeError("MPD builder must define 'domain'")
        cls._items[domain] = builder_class
        return builder_class

    @classmethod
    def get_mpd_builder_class(cls, domain: str) -> Optional[Type[BaseMpdBuilder]]:
        return cls._items.get(domain)

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        return list(cls._items.keys())


register_mpd = MpdRegistry.register


