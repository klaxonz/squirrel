from sites.proxy_config_origin import DomainConfig
from sites.proxy_config_registry import register_site_config, ProxyConfigProvider

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


@register_site_config
class BilibiliProxyConfig(ProxyConfigProvider):
    domain = 'bilibili.com'

    @classmethod
    def get_site_headers(cls) -> dict:
        return {
            'User-Agent': UA,
            'Referer': 'https://www.bilibili.com'
        }

    @classmethod
    def get_domain_configs(cls):
        return [
            DomainConfig(
                domain='bilibili.com',
                connect_timeout=30.0,
                read_timeout=120.0,
                max_retries=5,
                chunk_size=2 * 1024 * 1024,
                max_connections=50,
                keepalive_expiry=30.0,
                enable_http2=True,
            )
        ]
