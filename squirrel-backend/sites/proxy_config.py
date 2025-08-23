import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class NetworkConfig:
    """网络配置"""
    # 基础超时设置
    default_connect_timeout: float = 30.0
    default_read_timeout: float = 120.0
    default_write_timeout: float = 30.0
    default_pool_timeout: float = 10.0

    # 连接池设置
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0

    # 重试设置
    default_max_retries: int = 5
    max_retry_delay: float = 30.0
    retry_backoff_factor: float = 2.0

    # 块大小设置
    min_chunk_size: int = 256 * 1024  # 256KB
    default_chunk_size: int = 1024 * 1024  # 1MB
    max_chunk_size: int = 8 * 1024 * 1024  # 8MB

    # 性能优化
    enable_http2: bool = True
    enable_compression: bool = True

    @classmethod
    def from_env(cls) -> 'NetworkConfig':
        """从环境变量创建配置"""
        return cls(
            default_connect_timeout=float(os.getenv('PROXY_CONNECT_TIMEOUT', cls.default_connect_timeout)),
            default_read_timeout=float(os.getenv('PROXY_READ_TIMEOUT', cls.default_read_timeout)),
            default_write_timeout=float(os.getenv('PROXY_WRITE_TIMEOUT', cls.default_write_timeout)),
            default_pool_timeout=float(os.getenv('PROXY_POOL_TIMEOUT', cls.default_pool_timeout)),

            max_connections=int(os.getenv('PROXY_MAX_CONNECTIONS', cls.max_connections)),
            max_keepalive_connections=int(os.getenv('PROXY_MAX_KEEPALIVE', cls.max_keepalive_connections)),
            keepalive_expiry=float(os.getenv('PROXY_KEEPALIVE_EXPIRY', cls.keepalive_expiry)),

            default_max_retries=int(os.getenv('PROXY_MAX_RETRIES', cls.default_max_retries)),
            max_retry_delay=float(os.getenv('PROXY_MAX_RETRY_DELAY', cls.max_retry_delay)),
            retry_backoff_factor=float(os.getenv('PROXY_RETRY_BACKOFF', cls.retry_backoff_factor)),

            min_chunk_size=int(os.getenv('PROXY_MIN_CHUNK_SIZE', cls.min_chunk_size)),
            default_chunk_size=int(os.getenv('PROXY_DEFAULT_CHUNK_SIZE', cls.default_chunk_size)),
            max_chunk_size=int(os.getenv('PROXY_MAX_CHUNK_SIZE', cls.max_chunk_size)),

            enable_http2=os.getenv('PROXY_ENABLE_HTTP2', 'true').lower() == 'true',
            enable_compression=os.getenv('PROXY_ENABLE_COMPRESSION', 'true').lower() == 'true'
        )


@dataclass
class DomainConfig:
    """域名特定配置"""
    domain: str
    connect_timeout: float
    read_timeout: float
    max_retries: int
    chunk_size: int
    max_connections: int
    keepalive_expiry: float
    enable_http2: bool = True
    custom_headers: Optional[Dict[str, str]] = None


class ProxyConfigManager:
    """代理配置管理器

    变更：不再在此类中硬编码站点/域名的默认配置。
    各站点应在各自包内（如 sites/youtube/config.py）调用注册函数完成配置注入。
    """

    def __init__(self):
        self.network_config = NetworkConfig.from_env()
        # 域名 -> DomainConfig
        self._domain_configs: Dict[str, DomainConfig] = {}
        # 站点 -> 站点级默认 headers
        self._site_headers: Dict[str, Dict[str, str]] = {}
        # 域名 -> 站点标识
        self._domain_to_site: Dict[str, str] = {}

    # ---------------- 注册接口：供各站点模块调用 ----------------
    def register_site(self, site: str, site_headers: Optional[Dict[str, str]] = None):
        self._site_headers[site] = dict(site_headers or {})

    def register_domain(self, site: str, config: DomainConfig):
        self._domain_configs[config.domain] = config
        self._domain_to_site[config.domain] = site

    # ---------------- 查询接口 ----------------
    def get_domain_config(self, domain: str) -> Optional[DomainConfig]:
        """精确域名配置（兼容旧接口）"""
        return self._domain_configs.get(domain)

    def _suffix_lookup(self, host: str) -> Optional[str]:
        if not host:
            return None
        parts = host.split('.')
        candidates = ['.'.join(parts[i:]) for i in range(len(parts))]
        for cand in candidates:
            if cand in self._domain_configs:
                return cand
        return None

    def get_domain_config_by_host(self, host: str) -> Optional[DomainConfig]:
        key = self._suffix_lookup(host)
        return self._domain_configs.get(key) if key else None

    def get_effective_headers_by_host(self, host: str) -> Dict[str, str]:
        key = self._suffix_lookup(host)
        if not key:
            return {}
        site = self._domain_to_site.get(key)
        base = dict(self._site_headers.get(site, {})) if site else {}
        dom = self._domain_configs.get(key)
        if dom and dom.custom_headers:
            base.update(dom.custom_headers)
        return base


# 全局配置实例
_config_manager: Optional[ProxyConfigManager] = None


def get_config_manager() -> ProxyConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ProxyConfigManager()
    return _config_manager


def get_domain_config(domain: str) -> Optional[DomainConfig]:
    """精确获取域名配置（兼容旧接口）"""
    return get_config_manager().get_domain_config(domain)


register_site = lambda site, headers=None: get_config_manager().register_site(site, headers)
register_domain = lambda site, cfg: get_config_manager().register_domain(site, cfg)
