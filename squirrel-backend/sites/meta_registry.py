from typing import Dict, Type, Optional

from crawl import Video
from sites.registry_base import DomainRegistryBase


class MetaRegistry(DomainRegistryBase[Video]):
    kind = 'meta'

    @classmethod
    def get_meta_class(cls, domain: str) -> Optional[Type[Video]]:
        return cls.get_class(domain)

    @classmethod
    def get_all_meta_classes(cls) -> Dict[str, Type[Video]]:
        return cls.get_all()


register_meta = MetaRegistry.register
