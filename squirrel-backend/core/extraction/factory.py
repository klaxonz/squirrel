"""
提取器工厂和管理器
"""
import logging
from typing import Dict, Optional, List, Type
from urllib.parse import urlparse
from crawl import IExtractor
from utils.site_catalog import SiteCatalog

logger = logging.getLogger()


class ExtractorRegistry:
    """提取器注册表"""
    
    def __init__(self):
        self._extractors: Dict[str, Type[IExtractor]] = {}
        self._domain_mapping: Dict[str, str] = {}
        self._test_urls: Dict[str, str] = {}  # 存储每个站点的测试URL
    
    def register(self, site_name: str, extractor_class: Type[IExtractor], domains: List[str]) -> None:
        """注册提取器"""
        if site_name in self._extractors:
            logger.warning(f"提取器已存在，将被覆盖: {site_name}")
        
        self._extractors[site_name] = extractor_class
        
        # 建立域名映射
        for domain in domains:
            if domain in self._domain_mapping:
                logger.warning(f"域名映射已存在，将被覆盖: {domain} -> {site_name}")
            self._domain_mapping[domain] = site_name
        
        test_url = None
        if hasattr(extractor_class, 'get_test_url'):
            try:
                test_url = extractor_class.get_test_url()
            except Exception as e:
                logger.warning(f"调用 {site_name}.get_test_url() 失败: {e}")
                import traceback
                logger.info(traceback.format_exc())
        
        if test_url:
            self._test_urls[site_name] = test_url
            logger.info(f"✓ 注册提取器: {site_name}, 支持域名: {domains}, 测试URL: {test_url}")
        else:
            logger.info(f"✗ 注册提取器: {site_name}, 支持域名: {domains} (无测试URL)")
    
    def get_extractor_class(self, site_name: str) -> Optional[Type[IExtractor]]:
        """根据网站名获取提取器类"""
        return self._extractors.get(site_name)
    
    def get_site_by_domain(self, domain: str) -> Optional[str]:
        """根据域名获取网站名"""
        return self._domain_mapping.get(domain)
    
    def get_all_sites(self) -> List[str]:
        """获取所有支持的网站"""
        return list(self._extractors.keys())
    
    def get_all_domains(self) -> List[str]:
        """获取所有支持的域名"""
        return list(self._domain_mapping.keys())
    
    def get_test_url(self, site_name: str) -> Optional[str]:
        """获取站点的测试URL"""
        return self._test_urls.get(site_name)

    def clear(self) -> None:
        self._extractors.clear()
        self._domain_mapping.clear()
        self._test_urls.clear()


class ExtractorFactory:
    """提取器工厂"""
    
    def __init__(self, registry: ExtractorRegistry):
        self.registry = registry
        self._instances: Dict[str, IExtractor] = {}
    
    def create_extractor(self, url: str) -> Optional[IExtractor]:
        """根据URL创建提取器实例"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            if not SiteCatalog.is_site_enabled(domain=domain):
                logger.info(f"站点已禁用，跳过提取器创建: {domain}")
                return None
            
            # 尝试完整域名匹配
            site_name = self.registry.get_site_by_domain(domain)
            
            # 如果没有找到，尝试父域名匹配
            if not site_name:
                domain_parts = domain.split('.')
                for i in range(1, len(domain_parts)):
                    parent_domain = '.'.join(domain_parts[i:])
                    site_name = self.registry.get_site_by_domain(parent_domain)
                    if site_name:
                        break
            
            if not site_name:
                logger.warning(f"未找到支持的提取器: {domain}")
                return None
            
            # 获取或创建提取器实例
            if site_name not in self._instances:
                extractor_class = self.registry.get_extractor_class(site_name)
                if not extractor_class:
                    logger.error(f"提取器类未找到: {site_name}")
                    return None
                
                self._instances[site_name] = extractor_class()
            
            return self._instances[site_name]
        
        except Exception as e:
            logger.error(f"创建提取器失败: {url}, error: {e}")
            return None
    
    def get_extractor_by_site(self, site_name: str) -> Optional[IExtractor]:
        """根据网站名获取提取器实例"""
        if not SiteCatalog.is_site_enabled(site=site_name):
            logger.info(f"站点已禁用，跳过提取器获取: {site_name}")
            return None
        if site_name not in self._instances:
            extractor_class = self.registry.get_extractor_class(site_name)
            if not extractor_class:
                return None
            self._instances[site_name] = extractor_class()
        
        return self._instances[site_name]
    
    def clear_cache(self) -> None:
        """清空实例缓存"""
        self._instances.clear()


# 全局注册表和工厂实例
_global_registry = ExtractorRegistry()
_global_factory = ExtractorFactory(_global_registry)


def register_extractor(site_name: str, domains: List[str]):
    """装饰器：注册提取器"""
    def decorator(extractor_class: Type[IExtractor]):
        _global_registry.register(site_name, extractor_class, domains)
        return extractor_class
    return decorator


def get_extractor_factory() -> ExtractorFactory:
    """获取全局提取器工厂"""
    return _global_factory


def get_extractor_registry() -> ExtractorRegistry:
    """获取全局提取器注册表"""
    return _global_registry
