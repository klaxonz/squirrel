from typing import Dict, Type, Optional
from sites.registry_base import DomainRegistryBase


class IdExtractorRegistry(DomainRegistryBase):
    kind = 'id extractor'

    @classmethod
    def get_extractor(cls, domain: str) -> Optional[Type]:
        return cls.get_class(domain)

    @classmethod
    def get_all_extractors(cls) -> Dict[str, Type]:
        return cls.get_all()


register_extractor = IdExtractorRegistry.register
