from sites.proxy_config_origin import DomainConfig
from sites.proxy_config_registry import register_site_config, ProxyConfigProvider

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


@register_site_config
class JavdbProxyConfig(ProxyConfigProvider):
    domain = 'javdb.com'

    @classmethod
    def get_site_headers(cls) -> dict:
        return {
            'User-Agent': UA
        }

    @classmethod
    def get_domain_configs(cls):
        return [
            DomainConfig(
                domain='javdb.com',
                connect_timeout=45.0,
                read_timeout=150.0,
                max_retries=6,
                chunk_size=3 * 1024 * 1024,  # 3MB
                max_connections=30,
                keepalive_expiry=45.0,
                enable_http2=True
            )
        ]
