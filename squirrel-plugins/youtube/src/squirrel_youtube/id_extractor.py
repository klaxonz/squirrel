from crawl import RegexIdExtractor


class YoutubeIdExtractor(RegexIdExtractor):
    domain = 'youtube.com'
    pattern = r"(?:v=|/)([0-9A-Za-z_-]{11})"
