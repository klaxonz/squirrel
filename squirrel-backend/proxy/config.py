"""
代理配置模块

集中管理代理相关的配置参数，支持环境变量覆盖
"""

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
    """代理配置管理器"""
    
    def __init__(self):
        self.network_config = NetworkConfig.from_env()
        self._domain_configs: Dict[str, DomainConfig] = {}
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """初始化默认域名配置"""
        # Bilibili 配置 - 相对稳定的服务
        self._domain_configs['bilibili.com'] = DomainConfig(
            domain='bilibili.com',
            connect_timeout=30.0,
            read_timeout=120.0,
            max_retries=5,
            chunk_size=2 * 1024 * 1024,  # 2MB
            max_connections=50,
            keepalive_expiry=30.0,
            enable_http2=True,
            custom_headers={
                'Referer': 'https://www.bilibili.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        # Javdb 配置 - 可能较慢的服务
        self._domain_configs['javdb.com'] = DomainConfig(
            domain='javdb.com',
            connect_timeout=45.0,
            read_timeout=150.0,
            max_retries=6,
            chunk_size=3 * 1024 * 1024,  # 3MB
            max_connections=30,
            keepalive_expiry=45.0,
            enable_http2=True,
            custom_headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://missav.ws/'
            }
        )
        
        # Pornhub 配置 - 大文件流媒体
        self._domain_configs['pornhub.com'] = DomainConfig(
            domain='pornhub.com',
            connect_timeout=30.0,
            read_timeout=180.0,
            max_retries=7,
            chunk_size=4 * 1024 * 1024,  # 4MB
            max_connections=40,
            keepalive_expiry=60.0,
            enable_http2=True,
            custom_headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.pornhub.com/'
            }
        )
    
    def get_domain_config(self, domain: str) -> Optional[DomainConfig]:
        """获取域名配置"""
        return self._domain_configs.get(domain)
    
    def set_domain_config(self, config: DomainConfig):
        """设置域名配置"""
        self._domain_configs[config.domain] = config
    
    def get_all_domains(self) -> list[str]:
        """获取所有支持的域名"""
        return list(self._domain_configs.keys())
    
    def update_domain_config(self, domain: str, **kwargs):
        """更新域名配置"""
        if domain in self._domain_configs:
            config = self._domain_configs[domain]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)


# 全局配置实例
_config_manager: Optional[ProxyConfigManager] = None


def get_config_manager() -> ProxyConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ProxyConfigManager()
    return _config_manager


def get_network_config() -> NetworkConfig:
    """获取网络配置"""
    return get_config_manager().network_config


def get_domain_config(domain: str) -> Optional[DomainConfig]:
    """获取域名配置"""
    return get_config_manager().get_domain_config(domain)
