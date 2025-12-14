from __future__ import annotations

import logging
from typing import Dict, List, Type

from .base import Plugin

logger = logging.getLogger()


_registry: Dict[str, Type[Plugin]] = {}


def reset_registry() -> None:
    _registry.clear()


def register_plugin(cls: Type[Plugin]) -> Type[Plugin]:
    """Class decorator to register a plugin class by its `name` attribute."""
    try:
        name = getattr(cls, "name")
        if not isinstance(name, str) or not name:
            raise ValueError("Plugin must define non-empty 'name' class attribute")
        if name in _registry:
            logger.info("[plugins] overriding plugin: %s", name)
        _registry[name] = cls
        logger.info("[plugins] registered: %s", name)
    except Exception as e:
        logger.error("[plugins] failed to register %s: %s", getattr(cls, "__name__", cls), e)
    return cls


def all_plugin_classes() -> Dict[str, Type[Plugin]]:
    return dict(sorted(_registry.items(), key=lambda item: item[0]))


def instantiate_all() -> List[Plugin]:
    plugins: List[Plugin] = []
    for name, cls in _registry.items():
        try:
            inst: Plugin = cls()  # type: ignore[call-arg]
            plugins.append(inst)
        except Exception as e:
            logger.error("[plugins] failed to instantiate %s: %s", name, e)
    return plugins


