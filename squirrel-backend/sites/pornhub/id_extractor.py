import re

from sites.id_extractor import IdExtractor
from sites.id_extractor_registry import register_extractor


@register_extractor
class PornhubIdExtractor(IdExtractor):
    domain = 'pornhub.com'

    def extract_id(self):
        pattern = r"viewkey=([^&]+)"
        match = re.search(pattern, self.url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid url")