"""策略注册表"""
import logging
from typing import Dict, Optional
from .base import UpdateStrategy

logger = logging.getLogger()


class StrategyRegistry:
    """更新策略注册表"""
    
    _strategies: Dict[str, UpdateStrategy] = {}
    
    @classmethod
    def register(cls, strategy: UpdateStrategy):
        """注册策略"""
        cls._strategies[strategy.site_name] = strategy
        logger.info(f"Registered update strategy: {strategy.site_name}")
    
    @classmethod
    def get_strategy(cls, site_name: str) -> Optional[UpdateStrategy]:
        """获取策略"""
        return cls._strategies.get(site_name)
    
    @classmethod
    def get_all_sites(cls) -> list[str]:
        """获取所有支持的站点"""
        return list(cls._strategies.keys())


def update_strategy(site_name: str):
    """策略注册装饰器"""
    def decorator(cls):
        instance = cls()
        StrategyRegistry.register(instance)
        return cls
    return decorator

