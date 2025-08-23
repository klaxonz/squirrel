from urllib.parse import urlparse
from sites.subscription_origin import BaseSubscription
from sites.subscription_registry import SubscriptionRegistry


class SubscriptionFactory:
    """Factory class for creating subscription instances"""

    @classmethod
    def create_subscription(cls, url: str) -> BaseSubscription:
        """Create a subscription instance for the given URL"""
        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split('.')

        for i in range(len(domain_parts) - 1):
            current_domain = '.'.join(domain_parts[i:])
            channel_class = SubscriptionRegistry.get_channel_class(current_domain)
            if channel_class:
                return channel_class(url)

        raise ValueError(f"Unsupported url: {url}")

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        """Get list of supported platform domains"""
        return SubscriptionRegistry.get_supported_domains()
