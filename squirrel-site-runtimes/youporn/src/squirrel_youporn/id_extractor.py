from crawl import RegexIdExtractor


class YouPornIdExtractor(RegexIdExtractor):
    domain = "youporn.com"
    pattern = r"/watch/(\d+)/"
