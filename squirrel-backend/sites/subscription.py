from urllib.parse import urlparse
from sites.subscription_origin import BaseSubscription
from sites.subscription_registry import SubscriptionRegistry


class SubscriptionFactory:  # deprecated shim

    @classmethod
    def create_subscription(cls, url: str) -> BaseSubscription:
        from crawl import SubscriptionFactory as SdkSubscriptionFactory  # type: ignore

        # Fallback to legacy registry if SDK cannot resolve
        try:
            return SdkSubscriptionFactory.create_subscription(url)  # type: ignore[return-value]
        except Exception:
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
        try:
            from crawl import SubscriptionFactory as SdkSubscriptionFactory  # type: ignore
            return SdkSubscriptionFactory.get_supported_domains()  # type: ignore[return-value]
        except Exception:
            return SubscriptionRegistry.get_supported_domains()
