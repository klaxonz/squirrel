"""
插件系统与后端提取器工厂的桥接器

由于后端现在直接使用 SDK 的统一注册表，桥接器的职责已大大简化：
- 不再需要同步两个注册表
- 只需要在初始化时清理工厂缓存
- 提供刷新功能以支持热重载
"""
import logging

from crawl import get_extractor_registry
from utils.site_catalog import SiteCatalog
from .factory import get_extractor_factory, reset_factory

logger = logging.getLogger(__name__)


class PluginBridge:
    """插件系统桥接器

    由于后端现在直接使用 SDK 的统一注册表，桥接器只需要：
    1. 在初始化时清理工厂缓存
    2. 提供刷新功能以支持热重载
    """

    def __init__(self):
        self._initialized = False

    def initialize(self):
        """初始化插件桥接器"""
        if self._initialized:
            return

        try:
            registry = get_extractor_registry()
            factory = get_extractor_factory()
            factory.clear_cache()

            site_catalog = SiteCatalog.get_catalog() or {}
            registered_sites = []

            for site_name in registry.get_all_keys():
                catalog_entry = site_catalog.get(site_name.lower()) or {}
                if catalog_entry.get("enabled") is False:
                    logger.info(f"站点已禁用: {site_name}")
                    continue

                extractor = registry.get(site_name)
                if extractor:
                    domains = []
                    if isinstance(extractor, type):
                        domains = getattr(extractor, 'supported_domains', [])
                    else:
                        domains = getattr(extractor, 'supported_domains', [])

                    registered_sites.append(site_name)
                    logger.info(f"已注册提取器: {site_name}, 域名: {domains}")

            self._initialized = True
            logger.info(f"插件桥接器初始化完成，共 {len(registered_sites)} 个站点")

        except Exception as e:
            logger.error(f"插件桥接器初始化失败: {e}", exc_info=True)

    def refresh(self):
        """刷新插件注册"""
        self._initialized = False
        reset_factory()
        self.initialize()


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
