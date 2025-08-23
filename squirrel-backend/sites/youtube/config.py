"""YouTube 站点配置注册

将站点与域名配置注册到全局 ProxyConfigManager。
在 sites/__init__.py 导入本模块后自动生效。
"""
from sites.proxy_config import DomainConfig, register_site, register_domain

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# 站点级默认 headers（可被域名级覆盖）
register_site(
    'youtube',
    headers={
        'User-Agent': UA,
        'Referer': 'https://www.youtube.com/',
        'Origin': 'https://www.youtube.com',
    }
)

# 主站域
register_domain('youtube', DomainConfig(
    domain='youtube.com',
    connect_timeout=30.0,
    read_timeout=180.0,
    max_retries=6,
    chunk_size=2 * 1024 * 1024,  # 2MB
    max_connections=60,
    keepalive_expiry=45.0,
    enable_http2=True,
))

