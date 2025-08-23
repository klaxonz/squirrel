import logging
from typing import Dict, Type, Optional

logger = logging.getLogger(__name__)


class HandlerRegistry:

    _handlers: Dict[str, Type] = {}
    
    @classmethod
    def register(cls, handler_class: Type):
        if not hasattr(handler_class, 'domain') or not getattr(handler_class, 'domain'):
            raise AttributeError(
                f"Handler class '{handler_class.__name__}' must have a non-empty 'domain' class attribute to be registered."
            )

        domain = handler_class.domain

        if domain in cls._handlers:
            existing_class = cls._handlers[domain]
            logger.warning(
                f"Domain '{domain}' is already registered with '{existing_class.__name__}'. "
                f"It will be overridden by '{handler_class.__name__}'."
            )

        cls._handlers[domain] = handler_class
        logger.info(f"Registered handler '{handler_class.__name__}' for domain '{domain}'")
        return handler_class
    
    @classmethod
    def get_handler(cls, domain: str) -> Optional[Type]:
        return cls._handlers.get(domain)
    
    @classmethod
    def get_all_handlers(cls) -> Dict[str, Type]:
        return cls._handlers.copy()
    
    @classmethod
    def is_registered(cls, domain: str) -> bool:
        return domain in cls._handlers
    
    @classmethod
    def unregister(cls, domain: str) -> bool:
        if domain in cls._handlers:
            del cls._handlers[domain]
            logger.info(f"Unregistered handler for domain '{domain}'")
            return True
        return False
    
    @classmethod
    def clear_all(cls):
        cls._handlers.clear()
        logger.info("Cleared all registered handlers")
    
    @classmethod
    def get_supported_domains(cls) -> list:
        return list(cls._handlers.keys())


register_handler = HandlerRegistry.register

