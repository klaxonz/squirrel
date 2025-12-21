"""
提取器工厂 - 使用 SDK 统一注册表
"""
import logging
from typing import Dict, Optional, List, Type
from urllib.parse import urlparse

from crawl import Extractor, get_extractor_registry, PluginRegistry
from utils.site_catalog import SiteCatalog

logger = logging.getLogger()


class ExtractorFactory:
    """提取器工厂"""

    def __init__(self, registry: PluginRegistry):
        self.registry = registry
        self._instances: Dict[str, Extractor] = {}
        self._test_urls: Dict[str, str] = {}

    def create_extractor(self, url: str) -> Optional[Extractor]:
        """根据URL创建提取器实例"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            if not SiteCatalog.is_site_enabled(domain=domain):
                logger.info(f"站点已禁用，跳过提取器创建: {domain}")
                return None

            site_name = self.registry.get_by_domain(domain)

            if not site_name:
                domain_parts = domain.split('.')
                for i in range(1, len(domain_parts)):
                    parent_domain = '.'.join(domain_parts[i:])
                    site_name = self.registry.get_by_domain(parent_domain)
                    if site_name:
                        break

            if not site_name:
                logger.warning(f"未找到支持的提取器: {domain}")
                return None

            if site_name not in self._instances:
                extractor_class = self.registry.get(site_name)
                if not extractor_class:
                    logger.error(f"提取器类未找到: {site_name}")
                    return None

                if isinstance(extractor_class, type):
                    self._instances[site_name] = extractor_class()
                else:
                    self._instances[site_name] = extractor_class

            return self._instances[site_name]

        except Exception as e:
            logger.error(f"创建提取器失败: {url}, error: {e}")
            return None

    def get_extractor_by_site(self, site_name: str) -> Optional[Extractor]:
        """根据网站名获取提取器实例"""
        if not SiteCatalog.is_site_enabled(site=site_name):
            logger.info(f"站点已禁用，跳过提取器获取: {site_name}")
            return None
        if site_name not in self._instances:
            extractor_class = self.registry.get(site_name)
            if not extractor_class:
                return None
            if isinstance(extractor_class, type):
                self._instances[site_name] = extractor_class()
            else:
                self._instances[site_name] = extractor_class

        return self._instances[site_name]

    def clear_cache(self) -> None:
        """清空实例缓存"""
        self._instances.clear()

    def register(self, site_name: str, extractor_class: Type[Extractor], domains: List[str]) -> None:
        """注册提取器到 SDK 注册表"""
        self.registry.register(site_name, extractor_class, domains)

        test_url = None
        if hasattr(extractor_class, 'test_url'):
            test_url = getattr(extractor_class, 'test_url', None)
        elif hasattr(extractor_class, 'get_test_url'):
            try:
                test_url = extractor_class.get_test_url()
            except Exception as e:
                logger.warning(f"调用 {site_name}.get_test_url() 失败: {e}")

        if test_url:
            self._test_urls[site_name] = test_url
            logger.info(f"✓ 注册提取器: {site_name}, 支持域名: {domains}, 测试URL: {test_url}")
        else:
            logger.info(f"✗ 注册提取器: {site_name}, 支持域名: {domains} (无测试URL)")

    def get_test_url(self, site_name: str) -> Optional[str]:
        """获取站点的测试URL"""
        if site_name in self._test_urls:
            return self._test_urls[site_name]

        extractor_class = self.registry.get(site_name)
        if extractor_class:
            if hasattr(extractor_class, 'test_url'):
                return getattr(extractor_class, 'test_url', None)
        return None

    def get_all_sites(self) -> List[str]:
        """获取所有支持的网站"""
        return self.registry.get_all_keys()

    def get_all_domains(self) -> List[str]:
        """获取所有支持的域名"""
        return self.registry.get_all_domains()


_global_factory: Optional[ExtractorFactory] = None


def get_extractor_factory() -> ExtractorFactory:
    """获取全局提取器工厂"""
    global _global_factory
    if _global_factory is None:
        _global_factory = ExtractorFactory(get_extractor_registry())
    return _global_factory


def get_extractor_registry() -> PluginRegistry:
    """获取全局提取器注册表 (来自 SDK)"""
    from crawl import get_extractor_registry as sdk_get_extractor_registry
    return sdk_get_extractor_registry()


def reset_factory() -> None:
    """重置工厂实例"""
    global _global_factory
    if _global_factory:
        _global_factory.clear_cache()
    _global_factory = None
