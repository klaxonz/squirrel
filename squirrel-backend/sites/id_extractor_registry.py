import logging
from typing import Dict, Type, Optional

logger = logging.getLogger(__name__)


class IdExtractorRegistry:

    _extractors: Dict[str, Type] = {}

    @classmethod
    def register(cls, extractor_class: Type):
        if not hasattr(extractor_class, 'domain') or not getattr(extractor_class, 'domain'):
            raise AttributeError(
                f"Extractor class '{extractor_class.__name__}' must have a non-empty 'domain' class attribute to be registered."
            )

        domain = extractor_class.domain

        if domain in cls._extractors:
            existing_class = cls._extractors[domain]
            logger.warning(
                f"Domain '{domain}' is already registered with '{existing_class.__name__}'. "
                f"It will be overridden by '{extractor_class.__name__}'."
            )

        cls._extractors[domain] = extractor_class
        logger.info(f"Registered id extractor '{extractor_class.__name__}' for domain '{domain}'")
        return extractor_class

    @classmethod
    def get_extractor(cls, domain: str) -> Optional[Type]:
        return cls._extractors.get(domain)

    @classmethod
    def get_all_extractors(cls) -> Dict[str, Type]:
        return cls._extractors.copy()

    @classmethod
    def get_supported_domains(cls) -> list:
        return list(cls._extractors.keys())


register_extractor = IdExtractorRegistry.register

