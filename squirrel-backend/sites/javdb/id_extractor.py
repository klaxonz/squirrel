from sites.id_extractor import IdExtractor
from sites.id_extractor_registry import register_extractor


@register_extractor
class JavdbIdExtractor(IdExtractor):
    domain = 'javdb.com'

    def extract_id(self):
        return self.url.split('/')[-1]
