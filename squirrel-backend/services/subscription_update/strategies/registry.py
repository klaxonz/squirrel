"""Strategy registry"""
import logging
from collections.abc import Callable
from typing import Any

from .base import UpdateStrategy

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """Update strategy registry"""

    _strategies: dict[str, UpdateStrategy] = {}

    @classmethod
    def register(cls, strategy: UpdateStrategy) -> None:
        """Register a strategy"""
        cls._strategies[strategy.site_name] = strategy
        logger.info("Registered update strategy: %s", strategy.site_name)

    @classmethod
    def get_strategy(cls, site_name: str) -> UpdateStrategy | None:
        """Get a strategy"""
        return cls._strategies.get(site_name)

    @classmethod
    def get_all_sites(cls) -> list[str]:
        """Get all supported sites"""
        return list(cls._strategies.keys())


def update_strategy(site_name: str) -> Callable[[Any], Any]:
    """Strategy registration decorator"""
    def decorator(cls: Any) -> Any:
        instance = cls()
        StrategyRegistry.register(instance)
        return cls
    return decorator

