"""
插件系统与后端提取器工厂的桥接器
"""
import logging

from crawl import (
    get_extractor_registry as get_sdk_registry,
    IExtractor, ExtractionTask, ExtractionResult
)
from .factory import get_extractor_registry

logger = logging.getLogger(__name__)


class PluginExtractorAdapter(IExtractor):
    """适配器：将插件的提取器适配到后端的接口"""
    
    def __init__(self, plugin_extractor: IExtractor):
        self.plugin_extractor = plugin_extractor
        self.site_name = plugin_extractor.site_name
        self.supported_domains = plugin_extractor.supported_domains
    
    @property
    def supported_sites(self) -> list[str]:
        return self.plugin_extractor.supported_sites
    
    def can_handle(self, url: str) -> bool:
        return self.plugin_extractor.can_handle(url)
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        return self.plugin_extractor.extract(task)
    
    def validate_url(self, url: str) -> bool:
        return self.plugin_extractor.validate_url(url)


class PluginBridge:
    """插件系统桥接器"""
    
    def __init__(self):
        self._initialized = False
    
    def initialize(self):
        """初始化插件桥接器，将插件注册的提取器同步到后端工厂"""
        if self._initialized:
            return
        
        try:
            # 获取SDK中注册的提取器
            sdk_registry = get_sdk_registry()
            backend_registry = get_extractor_registry()
            
            # 遍历所有注册的站点
            for site_name in sdk_registry.get_all_sites():
                extractor_class = sdk_registry.get_extractor_class(site_name)
                if not extractor_class:
                    continue

                # 获取支持的域名（在当前循环中固化）
                domains = []
                if hasattr(extractor_class, 'supported_domains'):
                    domains = list(getattr(extractor_class, 'supported_domains', []) or [])

                # 为当前循环的 extractor_class 生成独立的适配器类，避免闭包晚绑定问题
                def _make_adapter(extractor_cls):
                    class AdapterClass(PluginExtractorAdapter):
                        def __init__(self):
                            plugin_instance = extractor_cls()
                            super().__init__(plugin_instance)

                    # 提高可读性：为不同站点赋予不同的类名
                    AdapterClass.__name__ = f"{extractor_cls.__name__}Adapter"
                    return AdapterClass

                AdapterClass = _make_adapter(extractor_class)

                # 注册到后端工厂
                backend_registry.register(site_name, AdapterClass, domains)
                logger.info(f"已桥接插件提取器: {site_name}, 域名: {domains}")
            
            self._initialized = True
            logger.info("插件桥接器初始化完成")
            
        except Exception as e:
            logger.error(f"插件桥接器初始化失败: {e}", exc_info=True)
    
    def refresh(self):
        """刷新插件注册，重新同步"""
        self._initialized = False
        self.initialize()


# 全局桥接器实例
_plugin_bridge = PluginBridge()


def initialize_plugin_bridge():
    """初始化插件桥接器"""
    _plugin_bridge.initialize()


def refresh_plugin_bridge():
    """刷新插件桥接器"""
    _plugin_bridge.refresh()


def get_plugin_bridge():
    """获取插件桥接器实例"""
    return _plugin_bridge
