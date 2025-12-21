from crawl import RegexIdExtractor, register_id_extractor


@register_id_extractor
class PornhubIdExtractor(RegexIdExtractor):
    domain = 'pornhub.com'
    pattern = r"viewkey=([^&]+)"
