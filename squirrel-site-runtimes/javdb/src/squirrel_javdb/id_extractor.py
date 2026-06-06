from __future__ import annotations

from crawl import RegexIdExtractor


class JavdbIdExtractor(RegexIdExtractor):
    domain = 'javdb.com'
    pattern = r'/v/([^/?#]+)/?$'


