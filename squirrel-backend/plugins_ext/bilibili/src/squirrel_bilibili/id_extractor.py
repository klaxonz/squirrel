from __future__ import annotations

import re

from crawl import IdExtractor, register_id_extractor


@register_id_extractor
class BilibiliIdExtractor(IdExtractor):
    domain = 'bilibili.com'

    def extract_id(self) -> str:
        pattern = r'BV[0-9A-Za-z]+'
        match = re.search(pattern, self.url)
        if match:
            return match.group(0)
        raise ValueError("Invalid url")


