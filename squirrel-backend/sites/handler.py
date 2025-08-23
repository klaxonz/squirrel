from abc import ABC, abstractmethod

from dto.video_dto import VideoUrlDto
from sites.handler_registry import HandlerRegistry
from models.video import Video


class VideoUrlHandler(ABC):
    """Abstract base class for video URL handlers"""

    # Optional domain attribute; subclasses can set this for registry use
    domain: str | None = None

    def __init__(self, url):
        self.url = url

    @abstractmethod
    def get_video_url(self, video: Video) -> VideoUrlDto:
        """
        Extract video and audio URLs for the given video

        Args:
            video: Video model instance

        Returns:
            VideoUrlDto containing video and audio URLs

        Raises:
            ValueError: If video URL extraction fails
            NotImplementedError: If platform is not supported
        """
        pass

    def supports_domain(self, domain: str) -> bool:
        """
        Default domain support checker based on the 'domain' class attribute.
        Handlers can override if they support multiple domains.
        """
        return getattr(self, "domain", None) == domain


class VideoUrlHandlerError(Exception):
    """Base exception for video URL handler errors"""
    pass


class UnsupportedDomainError(VideoUrlHandlerError):
    """Raised when a domain is not supported"""
    pass


class VideoUrlExtractionError(VideoUrlHandlerError):
    """Raised when video URL extraction fails"""
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
