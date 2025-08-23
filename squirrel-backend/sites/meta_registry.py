import logging
from typing import Dict, Type, Optional
from sites.meta_origin import Video

logger = logging.getLogger(__name__)


class MetaRegistry:
    _metas: Dict[str, Type[Video]] = {}

    @classmethod
    def register(cls, meta_class: Type[Video]):
        if not hasattr(meta_class, 'domain') or not getattr(meta_class, 'domain'):
            raise AttributeError(
                f"Meta class '{meta_class.__name__}' must have a non-empty 'domain' class attribute to be registered."
            )

        domain = meta_class.domain

        if domain in cls._metas:
            existing_class = cls._metas[domain]
            logger.warning(
                f"Domain '{domain}' is already registered with '{existing_class.__name__}'. "
                f"It will be overridden by '{meta_class.__name__}'."
            )

        cls._metas[domain] = meta_class
        logger.info(f"Registered meta class '{meta_class.__name__}' for domain '{domain}'")
        return meta_class

    @classmethod
    def get_meta_class(cls, domain: str) -> Optional[Type[Video]]:
        return cls._metas.get(domain)

    @classmethod
    def get_all_meta_classes(cls) -> Dict[str, Type[Video]]:
        return cls._metas.copy()

    @classmethod
    def get_supported_domains(cls) -> list:
        return list(cls._metas.keys())


register_meta = MetaRegistry.register

