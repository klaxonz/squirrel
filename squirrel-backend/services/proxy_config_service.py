from dataclasses import dataclass
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """代理配置数据类"""
    domain: str
    timeout: float = 120.0  # Increased default timeout
    chunk_size: int = 2 * 1024 * 1024  # 2MB default chunks
    max_retries: int = 5  # More retries for poor network
    connect_timeout: float = 30.0  # Connection timeout
    read_timeout: float = 120.0  # Read timeout
    max_connections: int = 100  # Connection pool size
    keepalive_expiry: float = 30.0  # Keep-alive duration
    enable_http2: bool = True  # Enable HTTP/2
    headers: Optional[Dict[str, str]] = None


class ProxyConfigService:
    """代理配置服务"""
    
    def __init__(self):
        self._configs: Dict[str, ProxyConfig] = {
            "bilibili.com": ProxyConfig(
                domain="bilibili.com",
                timeout=120.0,
                chunk_size=2 * 1024 * 1024,  # 2MB chunks
                max_retries=5,
                connect_timeout=30.0,
                read_timeout=120.0,
                max_connections=50,
                keepalive_expiry=30.0,
                enable_http2=True
            ),
            "javdb.com": ProxyConfig(
                domain="javdb.com",
                timeout=150.0,  # Longer timeout for potentially slower servers
                chunk_size=3 * 1024 * 1024,  # 3MB chunks
                max_retries=6,
                connect_timeout=45.0,
                read_timeout=150.0,
                max_connections=30,
                keepalive_expiry=45.0,
                enable_http2=True
            ),
            "pornhub.com": ProxyConfig(
                domain="pornhub.com",
                timeout=180.0,  # Longest timeout for media streaming
                chunk_size=4 * 1024 * 1024,  # 4MB chunks for large video files
                max_retries=7,
                connect_timeout=30.0,
                read_timeout=180.0,
                max_connections=40,
                keepalive_expiry=60.0,
                enable_http2=True
            ),
            "youtube.com": ProxyConfig(
                domain="youtube.com",
                timeout=180.0,
                chunk_size=2 * 1024 * 1024,
                max_retries=6,
                connect_timeout=30.0,
                read_timeout=180.0,
                max_connections=60,
                keepalive_expiry=45.0,
                enable_http2=True
            )
        }
    
    def get_config(self, domain: str) -> Optional[ProxyConfig]:
        """获取指定域名的代理配置"""
        return self._configs.get(domain)
    
    def get_all_configs(self) -> Dict[str, ProxyConfig]:
        """获取所有代理配置"""
        return self._configs.copy()
    
    def update_config(self, domain: str, config: ProxyConfig) -> None:
        """更新代理配置"""
        self._configs[domain] = config
        logger.info(f"Updated proxy config for domain: {domain}")
    
    def remove_config(self, domain: str) -> bool:
        """移除代理配置"""
        if domain in self._configs:
            del self._configs[domain]
            logger.info(f"Removed proxy config for domain: {domain}")
            return True
        return False


class ProxyConfigFactory:
    """代理配置工厂"""
    
    _instance: ProxyConfigService = None
    
    @classmethod
    def get_config_service(cls) -> ProxyConfigService:
        """获取配置服务实例（单例模式）"""
        if cls._instance is None:
            cls._instance = ProxyConfigService()
        return cls._instance
