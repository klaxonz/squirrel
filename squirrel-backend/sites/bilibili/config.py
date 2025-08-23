"""Bilibili 站点配置注册"""
from sites.proxy_config import DomainConfig, register_site, register_domain

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

register_site('bilibili', headers={'User-Agent': UA, 'Referer': 'https://www.bilibili.com'})

# 主站域
register_domain('bilibili', DomainConfig(
    domain='bilibili.com',
    connect_timeout=30.0,
    read_timeout=120.0,
    max_retries=5,
    chunk_size=2 * 1024 * 1024,
    max_connections=50,
    keepalive_expiry=30.0,
    enable_http2=True,
))

