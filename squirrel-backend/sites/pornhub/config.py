"""Pornhub 站点配置注册"""
from sites.proxy_config import DomainConfig, register_site, register_domain

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

register_site('pornhub', headers={'User-Agent': UA, 'Referer': 'https://www.pornhub.com/'})

# 主站域
register_domain('pornhub', DomainConfig(
    domain='pornhub.com',
    connect_timeout=30.0,
    read_timeout=180.0,
    max_retries=7,
    chunk_size=4 * 1024 * 1024,  # 4MB
    max_connections=40,
    keepalive_expiry=60.0,
    enable_http2=True,
))

