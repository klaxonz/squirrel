import logging
from typing import Dict, Type, Optional
from sites.proxy import VideoProxy

logger = logging.getLogger(__name__)


class ProxyRegistry:
    _proxies: Dict[str, Type[VideoProxy]] = {}

    @classmethod
    def register(cls, proxy_class: Type[VideoProxy]):
        if not hasattr(proxy_class, 'domain') or not getattr(proxy_class, 'domain'):
            raise AttributeError(
                f"Proxy class '{proxy_class.__name__}' must have a non-empty 'domain' class attribute to be registered."
            )

        domain = proxy_class.domain

        if domain in cls._proxies:
            existing_class = cls._proxies[domain]
            logger.warning(
                f"Domain '{domain}' is already registered with '{existing_class.__name__}'. "
                f"It will be overridden by '{proxy_class.__name__}'."
            )

        cls._proxies[domain] = proxy_class
        logger.info(f"Registered proxy '{proxy_class.__name__}' for domain '{domain}'")
        return proxy_class

    @classmethod
    def get_proxy_class(cls, domain: str) -> Optional[Type[VideoProxy]]:
        return cls._proxies.get(domain)


register_proxy = ProxyRegistry.register

