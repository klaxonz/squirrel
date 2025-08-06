from abc import ABC, abstractmethod
from dto.video_dto import VideoUrlDto
from models.video import Video


class VideoUrlHandler(ABC):
    """Abstract base class for video URL handlers"""
    
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
    
    @abstractmethod
    def supports_domain(self, domain: str) -> bool:
        """
        Check if this handler supports the given domain
        
        Args:
            domain: Domain name to check
            
        Returns:
            True if domain is supported, False otherwise
        """
        pass


class VideoUrlHandlerError(Exception):
    """Base exception for video URL handler errors"""
    pass


class UnsupportedDomainError(VideoUrlHandlerError):
    """Raised when a domain is not supported"""
    pass


class VideoUrlExtractionError(VideoUrlHandlerError):
    """Raised when video URL extraction fails"""
    pass
