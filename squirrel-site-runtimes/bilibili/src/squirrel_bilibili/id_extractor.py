from crawl import RegexIdExtractor


class BilibiliIdExtractor(RegexIdExtractor):
    domain = 'bilibili.com'
    pattern = r'BV[0-9A-Za-z]+'
    group_index = 0
