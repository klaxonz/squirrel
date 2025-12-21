from crawl import RegexIdExtractor, register_id_extractor


@register_id_extractor
class YoutubeIdExtractor(RegexIdExtractor):
    domain = 'youtube.com'
    pattern = r"(?:v=|/)([0-9A-Za-z_-]{11})"
