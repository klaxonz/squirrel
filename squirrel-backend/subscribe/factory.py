import importlib
import pkgutil
from typing import Dict, Type

from . import platforms
from .base import BaseSubscription


class SubscriptionFactory:
    """Factory class for creating subscription instances"""

    _subscriptions: Dict[str, Type[BaseSubscription]] = {}

    @classmethod
    def _register_platform(cls, domain: str, channel_class: Type[BaseSubscription]):
        """Register a platform implementation"""
        cls._subscriptions[domain] = channel_class

    @classmethod
    def _auto_discover(cls):
        """Auto discover and register platform implementations"""
        if not cls._subscriptions:  # Only discover if not already loaded
            # Import all modules in the platforms package
            for _, name, _ in pkgutil.iter_modules(platforms.__path__):
                importlib.import_module(f'.{name}', platforms.__package__)

            # Register platform implementations
            for platform_class in BaseSubscription.__subclasses__():
                # Get domain from class attributes or infer from class name
                domain = getattr(platform_class, 'DOMAIN', None)
                cls._register_platform(domain, platform_class)

    @classmethod
    def create_subscription(cls, url: str) -> BaseSubscription:
        """Create a subscription instance for the given URL"""
        cls._auto_discover()  # Ensure platforms are registered

        for domain, subscription_class in cls._subscriptions.items():
            if domain in url:
                return subscription_class(url)
        raise Exception(f'Unsupported url: {url}')

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        """Get list of supported platform domains"""
        cls._auto_discover()
        return list(cls._subscriptions.keys())
