from typing import Dict, Type, Optional
from sites.subscription_origin import BaseSubscription
from sites.registry_base import DomainRegistryBase


class SubscriptionRegistry(DomainRegistryBase[BaseSubscription]):
    kind = 'channel'

    @classmethod
    def get_channel_class(cls, domain: str) -> Optional[Type[BaseSubscription]]:
        return cls.get_class(domain)

    @classmethod
    def get_all_channel_classes(cls) -> Dict[str, Type[BaseSubscription]]:
        return cls.get_all()


subscription_channel = SubscriptionRegistry.register
