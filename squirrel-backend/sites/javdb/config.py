"""JavDB 站点配置注册"""
from sites.proxy_config import DomainConfig, register_site, register_domain

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

register_site('javdb', headers={'User-Agent': UA})

# 主站
register_domain('javdb', DomainConfig(
    domain='javdb.com',
    connect_timeout=45.0,
    read_timeout=150.0,
    max_retries=6,
    chunk_size=3 * 1024 * 1024,  # 3MB
    max_connections=30,
    keepalive_expiry=45.0,
    enable_http2=True,
    custom_headers={
        'Referer': 'https://missav.ws/'
    }
))


