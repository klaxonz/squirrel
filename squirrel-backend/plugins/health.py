from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class PluginHealth:
    """插件健康状态"""
    name: str
    healthy: bool
    message: str = ""
    last_check: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class HealthCheckable(Protocol):
    """支持健康检查的插件协议"""
    def health_check(self) -> Dict[str, Any]: ...


class PluginHealthChecker:
    """插件健康检查器"""

    def check(self, plugin: Any) -> PluginHealth:
        name = getattr(plugin, "name", plugin.__class__.__name__)
        try:
            if isinstance(plugin, HealthCheckable):
                result = plugin.health_check()
                return PluginHealth(
                    name=name,
                    healthy=result.get("healthy", True),
                    message=result.get("message", ""),
                    details=result.get("details", {})
                )
            return PluginHealth(name=name, healthy=True)
        except Exception as e:
            logger.warning("[health] check failed for %s: %s", name, e)
            return PluginHealth(name=name, healthy=False, message=str(e))

    def check_all(self, plugins: List[Any]) -> List[PluginHealth]:
        return [self.check(p) for p in plugins]

    def get_unhealthy(self, plugins: List[Any]) -> List[PluginHealth]:
        results = self.check_all(plugins)
        return [r for r in results if not r.healthy]
