from __future__ import annotations

from crawl import register_site_config, ProxyConfigProvider


@register_site_config
class JavdbProxyConfig(ProxyConfigProvider):
    domain = 'javdb.com'

    @classmethod
    def get_site_headers(cls):
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://javdb.com',
        }

    @classmethod
    def get_domain_configs(cls):
        from crawl import ProxyDomainConfig

        return [
            ProxyDomainConfig(
                domain='javdb.com',
                connect_timeout=30.0,
                read_timeout=120.0,
                max_retries=5,
                chunk_size=2 * 1024 * 1024,
                max_connections=50,
                keepalive_expiry=30.0,
                enable_http2=True,
            )
        ]
