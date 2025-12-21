from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from .base import Plugin

logger = logging.getLogger(__name__)


_registry: Dict[str, Type[Plugin]] = {}


def reset_registry() -> None:
    _registry.clear()


def register_plugin(cls: Type[Plugin]) -> Type[Plugin]:
    """Class decorator to register a plugin class by its `name` attribute."""
    cls_name = getattr(cls, "__name__", str(cls))
    try:
        name = getattr(cls, "name", None)
        if not isinstance(name, str) or not name:
            raise ValueError("Plugin must define non-empty 'name' class attribute")
        version = getattr(cls, "version", "unknown")
        if name in _registry:
            logger.info("[plugins] overriding plugin: %s (old: %s)", name, _registry[name].__name__)
        _registry[name] = cls
        logger.info("[plugins] registered: %s v%s (%s)", name, version, cls_name)
    except ValueError as e:
        logger.warning("[plugins] invalid plugin %s: %s", cls_name, e)
    except Exception as e:
        logger.error("[plugins] failed to register %s: %s", cls_name, e)
    return cls


def all_plugin_classes() -> Dict[str, Type[Plugin]]:
    return dict(sorted(_registry.items(), key=lambda item: item[0]))


def get_plugin_class(name: str) -> Optional[Type[Plugin]]:
    return _registry.get(name)


def instantiate_all() -> List[Plugin]:
    plugins: List[Plugin] = []
    for name, cls in _registry.items():
        try:
            inst: Plugin = cls()  # type: ignore[call-arg]
            plugins.append(inst)
            logger.debug("[plugins] instantiated: %s", name)
        except Exception as e:
            logger.error("[plugins] failed to instantiate %s: %s", name, e)
    logger.info("[plugins] instantiated %d plugin(s)", len(plugins))
    return plugins


