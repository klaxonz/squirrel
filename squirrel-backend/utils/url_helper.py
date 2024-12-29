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
