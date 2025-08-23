from typing import Type, Optional
from sites.registry_base import DomainRegistryBase


class SubtitlesRegistry(DomainRegistryBase):
    kind = 'subtitles'

    @classmethod
    def get_provider_class(cls, domain: str) -> Optional[Type]:
        return cls.get_class(domain)


register_subtitles = SubtitlesRegistry.register

