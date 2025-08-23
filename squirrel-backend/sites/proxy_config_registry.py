import logging
from typing import Dict, List, Optional, Type
from sites.proxy_config_origin import DomainConfig

logger = logging.getLogger(__name__)


class ProxyConfigProvider:

    domain: Optional[str] = None

    @classmethod
    def get_site_headers(cls) -> dict:
        return {}

    @classmethod
    def get_domain_configs(cls) -> List[DomainConfig]:
        return []


class ProxyConfigRegistry:
    _providers: Dict[str, Type[ProxyConfigProvider]] = {}

    @classmethod
    def register(cls, provider_cls: Type[ProxyConfigProvider]):
        domain = getattr(provider_cls, 'domain', None)
        if not domain:
            raise AttributeError(
                f"Config provider class '{provider_cls.__name__}' must have non-empty 'site' class attribute.")
        if domain in cls._providers:
            existing = cls._providers[domain]
            logger.warning(
                f"Site '{domain}' already registered with '{existing.__name__}', overriding with '{provider_cls.__name__}'.")
        cls._providers[domain] = provider_cls
        logger.info(f"Registered site config provider '{provider_cls.__name__}' for site '{domain}'")

        return provider_cls

    @classmethod
    def get_proxy_config_class(cls, domain: str) -> Optional[Type[ProxyConfigProvider]]:
        return cls._providers.get(domain)


register_site_config = ProxyConfigRegistry.register

