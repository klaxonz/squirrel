"""
代理模块初始化

提供视频代理服务的核心功能，包括：
- 网络优化和连接管理
- 自适应重试策略
- 健康监控
- 多域名支持
"""

from proxy.connection_manager import setup_domain_configs, cleanup_connections
from proxy.network_utils import get_health_monitor

__all__ = [
    'setup_domain_configs',
    'cleanup_connections',
    'get_health_monitor'
]


async def initialize_proxy_system():
    """初始化代理系统"""
    await setup_domain_configs()


async def shutdown_proxy_system():
    """关闭代理系统"""
    await cleanup_connections()