from typing import Type, Optional
from sites.registry_base import DomainRegistryBase


class ProxyRegistry(DomainRegistryBase):
    kind = 'proxy'

    @classmethod
    def get_proxy_class(cls, domain: str) -> Optional[Type]:
        return cls.get_class(domain)


register_proxy = ProxyRegistry.register
