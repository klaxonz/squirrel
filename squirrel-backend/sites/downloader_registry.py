import logging
from typing import Dict, Type, Optional

logger = logging.getLogger(__name__)


class DownloaderRegistry:

    _downloaders: Dict[str, Type] = {}
    
    @classmethod
    def register(cls, downloader_class: Type):
        if not hasattr(downloader_class, 'domain') or not getattr(downloader_class, 'domain'):
            raise AttributeError(
                f"Downloader class '{downloader_class.__name__}' must have a non-empty 'domain' class attribute to be registered."
            )

        domain = downloader_class.domain

        if domain in cls._downloaders:
            existing_class = cls._downloaders[domain]
            logger.warning(
                f"Domain '{domain}' is already registered with '{existing_class.__name__}'. "
                f"It will be overridden by '{downloader_class.__name__}'."
            )

        cls._downloaders[domain] = downloader_class
        logger.info(f"Registered downloader '{downloader_class.__name__}' for domain '{domain}'")
        return downloader_class
    
    @classmethod
    def get_downloader(cls, domain: str) -> Optional[Type]:
        return cls._downloaders.get(domain)
    
    @classmethod
    def get_all_downloaders(cls) -> Dict[str, Type]:
        return cls._downloaders.copy()
    
    @classmethod
    def is_registered(cls, domain: str) -> bool:
        return domain in cls._downloaders
    
    @classmethod
    def unregister(cls, domain: str) -> bool:
        if domain in cls._downloaders:
            del cls._downloaders[domain]
            logger.info(f"Unregistered downloader for domain '{domain}'")
            return True
        return False
    
    @classmethod
    def clear_all(cls):
        cls._downloaders.clear()
        logger.info("Cleared all registered downloaders")
    
    @classmethod
    def get_supported_domains(cls) -> list:
        return list(cls._downloaders.keys())


register_downloader = DownloaderRegistry.register
