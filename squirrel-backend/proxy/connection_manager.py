import asyncio
import logging
from typing import Dict, Optional
import httpx
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """连接配置"""
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0
    connect_timeout: float = 30.0
    read_timeout: float = 120.0
    write_timeout: float = 30.0
    pool_timeout: float = 10.0
    enable_http2: bool = True


class ConnectionManager:
    """连接管理器 - 单例模式管理HTTP连接池"""
    
    _instance: Optional['ConnectionManager'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._clients: Dict[str, httpx.AsyncClient] = {}
        self._configs: Dict[str, ConnectionConfig] = {}
        self._default_config = ConnectionConfig()
        
    @classmethod
    async def get_instance(cls) -> 'ConnectionManager':
        """获取单例实例"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def set_domain_config(self, domain: str, config: ConnectionConfig):
        """设置特定域名的连接配置"""
        self._configs[domain] = config
        logger.info(f"Set connection config for domain {domain}")
    
    def _get_config(self, domain: str) -> ConnectionConfig:
        """获取域名配置，如果没有则使用默认配置"""
        return self._configs.get(domain, self._default_config)
    
    async def get_client(self, domain: str) -> httpx.AsyncClient:
        """获取或创建指定域名的HTTP客户端"""
        if domain not in self._clients:
            config = self._get_config(domain)
            
            timeout = httpx.Timeout(
                connect=config.connect_timeout,
                read=config.read_timeout,
                write=config.write_timeout,
                pool=config.pool_timeout
            )
            
            limits = httpx.Limits(
                max_connections=config.max_connections,
                max_keepalive_connections=config.max_keepalive_connections,
                keepalive_expiry=config.keepalive_expiry
            )
            
            client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
                http2=config.enable_http2
            )
            
            self._clients[domain] = client
            logger.info(f"Created new HTTP client for domain {domain}")
            
        return self._clients[domain]
    
    async def close_client(self, domain: str):
        """关闭指定域名的客户端"""
        if domain in self._clients:
            await self._clients[domain].aclose()
            del self._clients[domain]
            logger.info(f"Closed HTTP client for domain {domain}")
    
    async def close_all(self):
        """关闭所有客户端"""
        for domain in list(self._clients.keys()):
            await self.close_client(domain)
        logger.info("Closed all HTTP clients")
    
    async def health_check(self, domain: str) -> bool:
        """检查指定域名的连接健康状态"""
        try:
            client = await self.get_client(domain)
            # 简单的健康检查 - 尝试连接
            response = await client.head(f"https://{domain}", timeout=10.0)
            return response.status_code < 500
        except Exception as e:
            logger.warning(f"Health check failed for {domain}: {e}")
            return False


# 全局连接管理器实例
_connection_manager: Optional[ConnectionManager] = None


async def get_connection_manager() -> ConnectionManager:
    """获取全局连接管理器实例"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = await ConnectionManager.get_instance()
    return _connection_manager


async def setup_domain_configs():
    """设置各域名的连接配置"""
    manager = await get_connection_manager()
    
    # Bilibili配置
    manager.set_domain_config("bilibili.com", ConnectionConfig(
        max_connections=50,
        max_keepalive_connections=20,
        keepalive_expiry=30.0,
        connect_timeout=30.0,
        read_timeout=120.0,
        enable_http2=True
    ))
    
    # Javdb配置
    manager.set_domain_config("javdb.com", ConnectionConfig(
        max_connections=30,
        max_keepalive_connections=15,
        keepalive_expiry=45.0,
        connect_timeout=45.0,
        read_timeout=150.0,
        enable_http2=True
    ))
    
    # Pornhub配置
    manager.set_domain_config("pornhub.com", ConnectionConfig(
        max_connections=40,
        max_keepalive_connections=20,
        keepalive_expiry=60.0,
        connect_timeout=30.0,
        read_timeout=180.0,
        enable_http2=True
    ))
    
    logger.info("Domain connection configs initialized")


async def cleanup_connections():
    """清理所有连接"""
    global _connection_manager
    if _connection_manager:
        await _connection_manager.close_all()
        _connection_manager = None
