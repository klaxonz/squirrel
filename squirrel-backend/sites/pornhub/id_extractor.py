import re

from sites.id_extractor import IdExtractor


class PornhubExtractor(IdExtractor):

    @classmethod
    def is_suitable(cls, url):
        return "pornhub.com" in url

    def extract_id(self):
        pattern = r"viewkey=([^&]+)"
        match = re.search(pattern, self.url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid url")