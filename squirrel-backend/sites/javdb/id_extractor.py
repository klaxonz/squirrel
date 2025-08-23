import re

from sites.id_extractor import IdExtractor


class JavdbExtractor(IdExtractor):

    @classmethod
    def is_suitable(cls, url):
        return "javdb.com" in url

    def extract_id(self):
        return self.url.split('/')[-1]