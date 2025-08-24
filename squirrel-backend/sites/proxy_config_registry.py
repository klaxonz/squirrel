import httpx
from typing import List, Optional, Type, Dict, Any
from sites.proxy_config_origin import DomainConfig
from sites.registry_base import DomainRegistryBase


class ProxyConfigProvider:

    domain: Optional[str] = None

    @classmethod
    def get_site_headers(cls) -> Dict[str, str]:
        return {}

    @classmethod
    def get_domain_configs(cls) -> List[DomainConfig]:
        return []
    
    @classmethod
    def get_client_config(cls) -> Dict[str, Any]:
        domain_configs = cls.get_domain_configs()
        
        if domain_configs:
            config = domain_configs[0]
            return {
                'timeout': httpx.Timeout(
                    connect=config.connect_timeout,
                    read=config.read_timeout,
                    write=config.read_timeout,
                    pool=config.read_timeout
                ),
                'limits': httpx.Limits(
                    max_keepalive_connections=config.max_connections // 2,
                    max_connections=config.max_connections,
                    keepalive_expiry=config.keepalive_expiry
                ),
                'follow_redirects': True,
                'http2': config.enable_http2
            }
        
        return {
            'timeout': httpx.Timeout(120.0, connect=30.0),
            'limits': httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            ),
            'follow_redirects': True,
            'http2': True
        }


class ProxyConfigRegistry(DomainRegistryBase[ProxyConfigProvider]):
    kind = 'site config provider'

    @classmethod
    def register(cls, provider_cls: Type[ProxyConfigProvider]):
        return super().register(provider_cls)

    @classmethod
    def get_proxy_config_class(cls, domain: str) -> Optional[Type[ProxyConfigProvider]]:
        return cls.get_class(domain)


register_site_config = ProxyConfigRegistry.register

