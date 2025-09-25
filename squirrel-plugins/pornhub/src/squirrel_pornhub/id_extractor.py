from __future__ import annotations

import re

from crawl import IdExtractor, register_id_extractor


@register_id_extractor
class PornhubIdExtractor(IdExtractor):
    domain = 'pornhub.com'

    def extract_id(self) -> str:
        pattern = r"viewkey=([^&]+)"
        match = re.search(pattern, self.url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid url")


