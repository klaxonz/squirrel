from dataclasses import dataclass
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """代理配置数据类"""
    domain: str
    timeout: float = 60.0
    chunk_size: int = 1024 * 1024 * 5
    max_retries: int = 3
    headers: Optional[Dict[str, str]] = None


class ProxyConfigService:
    """代理配置服务"""
    
    def __init__(self):
        self._configs: Dict[str, ProxyConfig] = {
            "bilibili.com": ProxyConfig(
                domain="bilibili.com",
                timeout=60.0,
                chunk_size=1024 * 1024 * 2,
                max_retries=3
            ),
            "javdb.com": ProxyConfig(
                domain="javdb.com", 
                timeout=90.0,
                chunk_size=1024 * 1024 * 5,
                max_retries=5
            ),
            "pornhub.com": ProxyConfig(
                domain="pornhub.com",
                timeout=120.0,
                chunk_size=1024 * 1024 * 3,
                max_retries=3
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
