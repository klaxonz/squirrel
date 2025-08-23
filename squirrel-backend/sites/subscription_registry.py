import logging
from typing import Dict, Type, Optional
from sites.subscription_origin import BaseSubscription

logger = logging.getLogger(__name__)


class SubscriptionRegistry:
    _channels: Dict[str, Type[BaseSubscription]] = {}

    @classmethod
    def register(cls, channel_class: Type[BaseSubscription]):
        if not hasattr(channel_class, 'domain') or not getattr(channel_class, 'domain'):
            raise AttributeError(
                f"Channel class '{channel_class.__name__}' must have a non-empty 'domain' class attribute to be registered."
            )

        domain = channel_class.domain

        if domain in cls._channels:
            existing_class = cls._channels[domain]
            logger.warning(
                f"Domain '{domain}' is already registered with '{existing_class.__name__}'. "
                f"It will be overridden by '{channel_class.__name__}'."
            )

        cls._channels[domain] = channel_class
        logger.info(f"Registered channel '{channel_class.__name__}' for domain '{domain}'")
        return channel_class

    @classmethod
    def get_channel_class(cls, domain: str) -> Optional[Type[BaseSubscription]]:
        return cls._channels.get(domain)

    @classmethod
    def get_all_channel_classes(cls) -> Dict[str, Type[BaseSubscription]]:
        return cls._channels.copy()

    @classmethod
    def get_supported_domains(cls) -> list:
        return list(cls._channels.keys())


subscription_channel = SubscriptionRegistry.register

