from sites.proxy_config_registry import ProxyConfigRegistry, ProxyConfigProvider


class ProxyConfigFactory:
    @staticmethod
    def create_proxy_config(domain: str) -> ProxyConfigProvider:
        proxy_class = ProxyConfigRegistry.get_proxy_config_class(domain)
        if proxy_class:
            return proxy_class()

        raise ValueError(f"No proxy registered for domain: {domain}")
