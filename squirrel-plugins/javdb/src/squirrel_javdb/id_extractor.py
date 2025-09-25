from __future__ import annotations

from crawl import IdExtractor, register_id_extractor


@register_id_extractor
class JavdbIdExtractor(IdExtractor):
    domain = 'javdb.com'

    def extract_id(self) -> str:
        return self.url.split('/')[-1]


