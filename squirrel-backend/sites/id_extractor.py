from abc import ABC, abstractmethod
from urllib.parse import urlparse
from sites.id_extractor_registry import IdExtractorRegistry


class IdExtractor(ABC):
    domain: str | None = None

    def __init__(self, url):
        self.url = url

    @abstractmethod
    def extract_id(self) -> str:
        raise NotImplementedError


class IdExtractorFactory:

    @classmethod
    def get(cls, url) -> IdExtractor:
        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split('.')

        for i in range(len(domain_parts) - 1):
            current_domain = '.'.join(domain_parts[i:])
            extractor_class = IdExtractorRegistry.get_extractor(current_domain)
            if extractor_class:
                return extractor_class(url)

        raise ValueError(f"No suitable ID extractor found for URL: {url}")


def extract_id_from_url(url: str) -> str:
    extractor = IdExtractorFactory.get(url)
    return extractor.extract_id()
