"""策略注册表"""
import logging
from collections.abc import Callable
from typing import Any

from .base import UpdateStrategy

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """更新策略注册表"""

    _strategies: dict[str, UpdateStrategy] = {}

    @classmethod
    def register(cls, strategy: UpdateStrategy) -> None:
        """注册策略"""
        cls._strategies[strategy.site_name] = strategy
        logger.info("Registered update strategy: %s", strategy.site_name)

    @classmethod
    def get_strategy(cls, site_name: str) -> UpdateStrategy | None:
        """获取策略"""
        return cls._strategies.get(site_name)

    @classmethod
    def get_all_sites(cls) -> list[str]:
        """获取所有支持的站点"""
        return list(cls._strategies.keys())


def update_strategy(site_name: str) -> Callable[[Any], Any]:
    """策略注册装饰器"""
    def decorator(cls: Any) -> Any:
        instance = cls()
        StrategyRegistry.register(instance)
        return cls
    return decorator

