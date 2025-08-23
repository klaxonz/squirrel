import re

from sites.id_extractor import IdExtractor


class YoutubeIdExtractor(IdExtractor):

    @classmethod
    def is_suitable(cls, url):
        return "youtube.com" in url

    def extract_id(self):
        pattern = r"(?:v=|/)([0-9A-Za-z_-]{11})"
        match = re.search(pattern, self.url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid url")
