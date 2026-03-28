from __future__ import annotations

from crawl import IdExtractor


class JavdbIdExtractor(IdExtractor):
    domain = 'javdb.com'

    def extract_id(self) -> str:
        return self.url.split('/')[-1]


