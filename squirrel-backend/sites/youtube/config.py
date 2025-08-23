from sites.proxy_config_origin import DomainConfig
from sites.proxy_config_registry import register_site_config, ProxyConfigProvider

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


@register_site_config
class YoutubeProxyConfig(ProxyConfigProvider):
    domain = 'youtube.com'

    @classmethod
    def get_site_headers(cls) -> dict:
        return {
            'User-Agent': UA,
            'Referer': 'https://www.youtube.com/',
            'Origin': 'https://www.youtube.com',
        }

    @classmethod
    def get_domain_configs(cls):
        return [
            DomainConfig(
                domain='youtube.com',
                connect_timeout=30.0,
                read_timeout=180.0,
                max_retries=6,
                chunk_size=2 * 1024 * 1024,  # 2MB
                max_connections=60,
                keepalive_expiry=45.0,
                enable_http2=True,
            )
        ]
