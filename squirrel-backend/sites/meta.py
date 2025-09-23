from urllib.parse import urlparse
from crawl import Video
from sites.meta_registry import MetaRegistry


class VideoFactory:
    @staticmethod
    def create_video(url, video_info) -> Video:
        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split('.')

        for i in range(len(domain_parts) - 1):
            current_domain = '.'.join(domain_parts[i:])
            meta_class = MetaRegistry.get_meta_class(current_domain)
            if meta_class:
                return meta_class(url, video_info)

        raise ValueError(f"No meta class found for url {url}")

