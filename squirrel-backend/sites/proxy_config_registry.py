from typing import List, Optional, Type
from sites.proxy_config_origin import DomainConfig
from sites.registry_base import DomainRegistryBase


class ProxyConfigProvider:

    domain: Optional[str] = None

    @classmethod
    def get_site_headers(cls) -> dict:
        return {}

    @classmethod
    def get_domain_configs(cls) -> List[DomainConfig]:
        return []


class ProxyConfigRegistry(DomainRegistryBase[ProxyConfigProvider]):
    kind = 'site config provider'

    @classmethod
    def register(cls, provider_cls: Type[ProxyConfigProvider]):
        return super().register(provider_cls)

    @classmethod
    def get_proxy_config_class(cls, domain: str) -> Optional[Type[ProxyConfigProvider]]:
        return cls.get_class(domain)


register_site_config = ProxyConfigRegistry.register

