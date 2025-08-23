from abc import ABC, abstractmethod

from schemas.video.dto.video_dto import VideoUrlDto
from sites.handler_registry import HandlerRegistry
from models.video import Video


class VideoUrlHandler(ABC):

    domain: str | None = None

    @abstractmethod
    def get_video_url(self, video: Video) -> VideoUrlDto:
        pass

    def supports_domain(self, domain: str) -> bool:
        return getattr(self, "domain", None) == domain


class VideoUrlHandlerError(Exception):
    pass


class UnsupportedDomainError(VideoUrlHandlerError):
    pass


class VideoUrlExtractionError(VideoUrlHandlerError):
    pass


class VideoUrlHandlerFactory:

    @classmethod
    def get_handler(cls, domain: str) -> VideoUrlHandler:
        handler_class = HandlerRegistry.get_handler(domain)
        if not handler_class:
            raise UnsupportedDomainError(f"No handler found for domain: {domain}")
        return handler_class()

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        return HandlerRegistry.get_supported_domains()
