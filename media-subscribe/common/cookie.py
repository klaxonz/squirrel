import http.cookiejar as cookielib
from .config import GlobalConfig
from .url_helper import extract_top_level_domain


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
