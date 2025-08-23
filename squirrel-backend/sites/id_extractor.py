from abc import ABC, abstractmethod

_extractors = []


def _register_extractor(extractor):
    _extractors.append(extractor)


class IdExtractor(ABC):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _register_extractor(cls)

    def __init__(self, url):
        self.url = url

    @classmethod
    @abstractmethod
    def is_suitable(cls, url) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract_id(self) -> str:
        raise NotImplementedError


class IdExtractorFactory:

    @classmethod
    def get(cls, url) -> IdExtractor:
        for extractor in _extractors:
            if extractor.is_suitable(url):
                return extractor(url)
        raise ValueError("Invalid url")


def extract_id_from_url(url: str) -> str:
    extractor = IdExtractorFactory.get(url)
    return extractor.extract_id()

