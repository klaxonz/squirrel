import importlib
import pkgutil
from typing import Dict, Type

from .base import BaseSubscribeChannel
from . import platforms

class SubscribeChannelFactory:
    """Factory class for creating channel subscription instances"""
    
    _channels: Dict[str, Type[BaseSubscribeChannel]] = {}

    @classmethod
    def _register_platform(cls, domain: str, channel_class: Type[BaseSubscribeChannel]):
        """Register a platform implementation"""
        cls._channels[domain] = channel_class

    @classmethod
    def _auto_discover(cls):
        """Auto discover and register platform implementations"""
        if not cls._channels:  # Only discover if not already loaded
            # Import all modules in the platforms package
            for _, name, _ in pkgutil.iter_modules(platforms.__path__):
                importlib.import_module(f'.{name}', platforms.__package__)

            # Register platform implementations
            for platform_class in BaseSubscribeChannel.__subclasses__():
                # Get domain from class attributes or infer from class name
                domain = getattr(platform_class, 'DOMAIN', None)
                if domain is None:
                    # Convert CamelCase to lowercase and remove 'SubscribeChannel'
                    name = platform_class.__name__.replace('SubscribeChannel', '')
                    domain = f"{name.lower()}.com"
                cls._register_platform(domain, platform_class)

    @classmethod
    def create_subscribe_channel(cls, url: str) -> BaseSubscribeChannel:
        """Create a channel subscription instance for the given URL"""
        cls._auto_discover()  # Ensure platforms are registered
        
        for domain, channel_class in cls._channels.items():
            if domain in url:
                return channel_class(url)
        raise Exception(f'Unsupported url: {url}')

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        """Get list of supported platform domains"""
        cls._auto_discover()
        return list(cls._channels.keys()) 