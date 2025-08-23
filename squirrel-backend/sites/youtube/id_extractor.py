import re

from sites.id_extractor import IdExtractor
from sites.id_extractor_registry import register_extractor


@register_extractor
class YoutubeIdExtractor(IdExtractor):
    domain = 'youtube.com'

    def extract_id(self):
        pattern = r"(?:v=|/)([0-9A-Za-z_-]{11})"
        match = re.search(pattern, self.url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid url")
