from sites.proxy_config_origin import DomainConfig
from sites.proxy_config_registry import register_site_config, ProxyConfigProvider

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


@register_site_config
class PornhubProxyConfig(ProxyConfigProvider):
    domain = 'pornhub.com'

    @classmethod
    def get_site_headers(cls) -> dict:
        return {
            'User-Agent': UA,
            'Referer': 'https://www.pornhub.com/'
        }

    @classmethod
    def get_domain_configs(cls):
        return [
            DomainConfig(
                domain='pornhub.com',
                connect_timeout=30.0,
                read_timeout=180.0,
                max_retries=7,
                chunk_size=4 * 1024 * 1024,  # 4MB
                max_connections=40,
                keepalive_expiry=60.0,
                enable_http2=True,
            )
        ]
