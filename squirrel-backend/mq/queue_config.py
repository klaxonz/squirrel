"""
消息队列配置管理

基于插件注册表动态生成队列配置，消除硬编码
"""
import logging
from typing import Dict, List
from enum import Enum

from utils.site_catalog import SiteCatalog

logger = logging.getLogger()


class QueueMode(str, Enum):
    """队列模式枚举"""
    MANUAL = 'manual'  # 手动触发（最高优先级）
    SCHEDULED = 'scheduled'  # 定时任务（用于 VIDEO_DOWNLOAD 等队列，VIDEO_EXTRACT 已弃用）
    INCREMENTAL = 'incremental'  # 增量更新（高优先级，用于 SUBSCRIPTION_UPDATE 和 VIDEO_EXTRACT）
    FULL = 'full'  # 全量更新（低优先级，用于 SUBSCRIPTION_UPDATE 和 VIDEO_EXTRACT）


class QueueType(str, Enum):
    """队列类型枚举"""
    VIDEO_EXTRACT = 'video:extract'
    SUBSCRIPTION_UPDATE = 'subscription:update'
    VIDEO_DOWNLOAD = 'video:download'


class QueueConfigManager:
    """队列配置管理器 - 基于插件注册表动态生成配置"""
    
    def __init__(self):
        self._domain_to_site: Dict[str, str] = {}
        self._initialized = False
    
    def initialize(self):
        """
        从插件注册表初始化配置
        必须在插件加载后调用
        """
        if self._initialized:
            return
        
        try:
            from crawl import get_extractor_registry
            registry = get_extractor_registry()
            
            # 从注册表获取所有站点和域名映射
            for domain in registry.get_all_domains():
                site = registry.get_site_by_domain(domain)
                if site:
                    if not SiteCatalog.is_site_enabled(site, domain):
                        logger.info(f"Skipping disabled site in queue config: site={site}, domain={domain}")
                        continue
                    self._domain_to_site[domain] = site
            
            self._initialized = True
            logger.info(f"Queue config initialized with {len(self._domain_to_site)} domains")
            
        except Exception as e:
            logger.error(f"Failed to initialize queue config: {e}")
    
    def get_supported_sites(self) -> List[str]:
        """获取所有支持的站点"""
        return list(set(self._domain_to_site.values()))
    
    def get_supported_domains(self) -> List[str]:
        """获取所有支持的域名"""
        return list(self._domain_to_site.keys())
    
    def get_domain_to_site_mapping(self) -> Dict[str, str]:
        """获取域名到站点的映射"""
        return self._domain_to_site.copy()
    
    def get_site_by_domain(self, domain: str) -> str:
        """根据域名获取站点名"""
        return self._domain_to_site.get(domain, '')
    
    def build_queue_name(self, queue_type: QueueType, site: str, mode: QueueMode) -> str:
        """构建队列名称"""
        return f'queue:{queue_type.value}:{site}:{mode.value}'
    
    def build_entry_queue(self, queue_type: QueueType, mode: QueueMode) -> str:
        """构建入口队列名称"""
        return f'queue:{queue_type.value}:{mode.value}'
    
    def get_all_modes(self) -> List[QueueMode]:
        """获取所有队列模式"""
        return list(QueueMode)
    
    def generate_domain_queue_mapping(self, queue_type: QueueType) -> Dict[str, Dict[str, str]]:
        """
        生成域队列映射
        """
        mapping = {}
        
        # 根据队列类型选择对应的模式
        if queue_type == QueueType.SUBSCRIPTION_UPDATE:
            modes = [QueueMode.MANUAL, QueueMode.INCREMENTAL, QueueMode.FULL]
        elif queue_type == QueueType.VIDEO_EXTRACT:
            # 视频提取也支持三种模式：手动、增量、全量
            modes = [QueueMode.MANUAL, QueueMode.INCREMENTAL, QueueMode.FULL]
        else:
            modes = [QueueMode.MANUAL, QueueMode.SCHEDULED]
        
        for domain, site in self._domain_to_site.items():
            mapping[domain] = {
                mode.value: self.build_queue_name(queue_type, site, mode)
                for mode in modes
            }
        return mapping


# 全局单例
_queue_config_manager: QueueConfigManager = None


def get_queue_config() -> QueueConfigManager:
    """获取队列配置管理器单例"""
    global _queue_config_manager
    if _queue_config_manager is None:
        _queue_config_manager = QueueConfigManager()
    return _queue_config_manager


def ensure_queue_config_initialized():
    """确保队列配置已初始化"""
    config = get_queue_config()
    if not config._initialized:
        config.initialize()


