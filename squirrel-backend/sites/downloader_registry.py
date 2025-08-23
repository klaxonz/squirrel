from typing import Dict, Type, Optional
from sites.registry_base import DomainRegistryBase


class DownloaderRegistry(DomainRegistryBase):
    kind = 'downloader'

    @classmethod
    def get_downloader(cls, domain: str) -> Optional[Type]:
        return cls.get_class(domain)

    @classmethod
    def get_all_downloaders(cls) -> Dict[str, Type]:
        return cls.get_all()


register_downloader = DownloaderRegistry.register
