from handlers.video_url.base import VideoUrlHandler, UnsupportedDomainError
from sites.bilibili.handler import BilibiliHandler
from handlers.video_url.youtube_handler import YouTubeHandler
from handlers.video_url.pornhub_handler import PornhubHandler
from handlers.video_url.javdb_handler import JavdbHandler


class VideoUrlHandlerFactory:
    """Factory for creating video URL handlers based on domain"""
    
    _handlers = [
        BilibiliHandler(),
        YouTubeHandler(),
        PornhubHandler(),
        JavdbHandler(),
    ]
    
    @classmethod
    def get_handler(cls, domain: str) -> VideoUrlHandler:
        """
        Get the appropriate handler for the given domain
        
        Args:
            domain: Domain name (e.g., 'bilibili.com', 'youtube.com')
            
        Returns:
            VideoUrlHandler instance for the domain
            
        Raises:
            UnsupportedDomainError: If no handler supports the domain
        """
        for handler in cls._handlers:
            if handler.supports_domain(domain):
                return handler
        
        raise UnsupportedDomainError(f"No handler found for domain: {domain}")
    
    @classmethod
    def get_supported_domains(cls) -> list[str]:
        """
        Get list of all supported domains
        
        Returns:
            List of supported domain names
        """
        domains = []
        test_domains = ['bilibili.com', 'youtube.com', 'pornhub.com', 'javdb.com']
        
        for domain in test_domains:
            for handler in cls._handlers:
                if handler.supports_domain(domain):
                    domains.append(domain)
                    break
        
        return domains
