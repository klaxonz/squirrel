import http.cookiejar as cookielib
from urllib.parse import urlencode

from .config import GlobalConfig


def extract_top_level_domain(url):
    """
    从URL中提取顶级域名（包括二级，如果存在的话，例如example.com）。

    :param url: 完整的URL字符串
    :return: 顶级域名字符串
    """
    from urllib.parse import urlparse

    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')

    # 通常，顶级域名是最后两个部分（考虑到可能有www的情况，或者是直接的顶级域名）
    # 如果域名只有两部分，直接返回，因为这是最简单的顶级域名情况（如example.com）
    if len(domain_parts) == 2:
        return parsed_url.netloc
    else:
        # 否则，提取最后两个部分作为顶级域名
        return '.'.join(domain_parts[-2:])


def filter_cookies_to_query_string(target_url):
    """
    筛选与目标URL匹配的所有相关Cookie，并转换为分号分隔的格式（k1=v1; k2=v2;）。

    :param target_url: 目标URL，用于确定需匹配的顶级域名
    :return: 筛选后Cookie的分号分隔格式字符串
    """
    file_path = GlobalConfig.get_cookies_file_path()
    cj = cookielib.MozillaCookieJar()
    cj.load(file_path, ignore_discard=True, ignore_expires=True)

    domain = extract_top_level_domain(target_url)
    filtered_cj = cookielib.CookieJar()

    for cookie in cj:
        if cookie.domain.endswith(domain):
            filtered_cj.set_cookie(cookie)

    # 手动构建分号分隔的Cookie字符串
    cookie_strings = [f"{cookie.name}={cookie.value}" for cookie in filtered_cj]
    cookie_semicolon_string = '; '.join(cookie_strings)
    return cookie_semicolon_string

