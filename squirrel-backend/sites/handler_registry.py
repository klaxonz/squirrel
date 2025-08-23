from typing import Type, Optional
from sites.registry_base import DomainRegistryBase


class HandlerRegistry(DomainRegistryBase):
    kind = 'handler'

    @classmethod
    def get_handler(cls, domain: str) -> Optional[Type]:
        return cls.get_class(domain)


register_handler = HandlerRegistry.register
