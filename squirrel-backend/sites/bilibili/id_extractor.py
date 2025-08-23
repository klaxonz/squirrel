import re
from sites.id_extractor import IdExtractor
from sites.id_extractor_registry import register_extractor


@register_extractor
class BilibiliIdExtractor(IdExtractor):
    domain = 'bilibili.com'

    def extract_id(self):
        pattern = r'BV[0-9A-Za-z]+'
        match = re.search(pattern, self.url)
        if match:
            return match.group(0)
        else:
            raise ValueError("Invalid url")