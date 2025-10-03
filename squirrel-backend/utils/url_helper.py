from typing import Optional
from urllib.parse import urlparse


def extract_top_level_domain(url):
    """
    从URL中提取顶级域名（包括二级，如果存在的话，例如example.com）。

    :param url: 完整的URL字符串
    :return: 顶级域名字符串
    """
    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')

    # 通常，顶级域名是最后两个部分（考虑到可能有www的情况，或者是直接的顶级域名）
    # 如果域名只有两部分，直接返回，因为这是最简单的顶级域名情况（如example.com）
    if len(domain_parts) == 2:
        return parsed_url.netloc
    else:
        # 否则，提取最后两个部分作为顶级域名
        return '.'.join(domain_parts[-2:])


def get_site_from_url(url: str) -> Optional[str]:
    """
    从 URL 获取站点名称（使用已注册的提取器映射）
    
    :param url: 完整的URL字符串
    :return: 站点名称，如果未找到则返回 None
    """
    if not url:
        return None
    try:
        from core.extraction.factory import get_extractor_registry
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # 使用已有的提取器注册表获取站点名
        registry = get_extractor_registry()
        site_name = registry.get_site_by_domain(domain)
        
        # 如果完整域名没找到，尝试父域名（移除 www. 等前缀）
        if not site_name and domain.startswith('www.'):
            domain = domain[4:]
            site_name = registry.get_site_by_domain(domain)
        
        return site_name
    except Exception:
        return None
