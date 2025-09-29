from __future__ import annotations

from crawl import register_site_config, ProxyConfigProvider, ProxyDomainConfig


@register_site_config
class YoutubeProxyConfig(ProxyConfigProvider):
    domain = 'youtube.com'

    @classmethod
    def get_site_headers(cls):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.youtube.com',
        }

    @classmethod
    def get_domain_configs(cls):
        return [
            ProxyDomainConfig(
                domain='youtube.com',
                connect_timeout=30.0,
                read_timeout=120.0,
                max_retries=5,
                chunk_size=2 * 1024 * 1024,
                max_connections=50,
                keepalive_expiry=30.0,
                enable_http2=True,
            )
        ]


