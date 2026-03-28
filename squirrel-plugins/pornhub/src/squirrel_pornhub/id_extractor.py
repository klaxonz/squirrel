from crawl import RegexIdExtractor


class PornhubIdExtractor(RegexIdExtractor):
    domain = 'pornhub.com'
    pattern = r"viewkey=([^&]+)"
