from crawl import create_site_config

JavdbProxyConfig = create_site_config(
    'javdb.com',
    referer='https://javdb.com',
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
)
