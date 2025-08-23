from typing import Dict, Type, Optional, Generic, TypeVar
import logging

T = TypeVar('T')
logger = logging.getLogger(__name__)


class DomainRegistryBase(Generic[T]):
    """
    Generic domain keyed registry base class.
    Subclasses get an independent storage dict via __init_subclass__.
    """
    # Attribute name on registered class used as the domain key
    attr_name: str = 'domain'
    # Human friendly kind name for logs
    kind: str = 'item'

    def __init_subclass__(cls, **kwargs):  # type: ignore[override]
        super().__init_subclass__(**kwargs)
        cls._items: Dict[str, Type[T]] = {}

    @classmethod
    def register(cls, item_class: Type[T]):
        domain = getattr(item_class, cls.attr_name, None)
        if not domain:
            raise AttributeError(
                f"{cls.kind.capitalize()} class '{item_class.__name__}' must have a non-empty "
                f"'{cls.attr_name}' class attribute to be registered."
            )
        if domain in cls._items:
            existing = cls._items[domain]
            logger.warning(
                f"Domain '{domain}' is already registered with '{existing.__name__}'. "
                f"It will be overridden by '{item_class.__name__}'."
            )
        cls._items[domain] = item_class
        logger.debug(f"Registered {cls.kind} '{item_class.__name__}' for domain '{domain}'")
        return item_class

    @classmethod
    def get_class(cls, domain: str) -> Optional[Type[T]]:
        return cls._items.get(domain)

    @classmethod
    def get_all(cls) -> Dict[str, Type[T]]:
        return cls._items.copy()

    @classmethod
    def is_registered(cls, domain: str) -> bool:
        return domain in cls._items

    @classmethod
    def unregister(cls, domain: str) -> bool:
        if domain in cls._items:
            del cls._items[domain]
            logger.info(f"Unregistered {cls.kind} for domain '{domain}'")
            return True
        return False

    @classmethod
    def clear_all(cls):
        cls._items.clear()
        logger.info(f"Cleared all registered {cls.kind}s")

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        return list(cls._items.keys())

