from crawl import create_site_config

YoutubeProxyConfig = create_site_config(
    'youtube.com',
    referer='https://www.youtube.com',
)
