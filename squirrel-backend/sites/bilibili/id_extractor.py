import re

from sites.id_extractor import IdExtractor


class BilibiliIdExtractor(IdExtractor):

    @classmethod
    def is_suitable(cls, url):
        return "bilibili.com" in url

    def extract_id(self):
        pattern = r'BV[0-9A-Za-z]+'
        match = re.search(pattern, self.url)
        if match:
            return match.group(0)
        else:
            raise ValueError("Invalid url")