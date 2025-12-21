from crawl import RegexIdExtractor, register_id_extractor


@register_id_extractor
class BilibiliIdExtractor(RegexIdExtractor):
    domain = 'bilibili.com'
    pattern = r'BV[0-9A-Za-z]+'
    group_index = 0
