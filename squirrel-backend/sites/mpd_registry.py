from typing import Type, Optional
from sites.registry_base import DomainRegistryBase


class MpdRegistry(DomainRegistryBase):
    kind = 'mpd'

    @classmethod
    def get_mpd_builder_class(cls, domain: str) -> Optional[Type]:
        return cls.get_class(domain)


register_mpd = MpdRegistry.register

