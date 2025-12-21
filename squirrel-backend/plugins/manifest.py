"""
插件清单模块 - 版本管理和兼容性检查
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)

SDK_VERSION = "2.0.0"


@dataclass
class PluginManifest:
    """插件清单"""
    name: str
    version: str
    min_sdk_version: Optional[str] = None
    max_sdk_version: Optional[str] = None
    dependencies: Dict[str, str] = field(default_factory=dict)

    def is_compatible(self, sdk_version: Optional[str] = None) -> bool:
        sdk_ver = sdk_version or SDK_VERSION
        try:
            from packaging.version import Version
            current = Version(sdk_ver)

            if self.min_sdk_version:
                if current < Version(self.min_sdk_version):
                    return False

            if self.max_sdk_version:
                if current > Version(self.max_sdk_version):
                    return False

            return True
        except ImportError:
            return self._simple_version_check(sdk_ver)
        except Exception as e:
            logger.warning(f"版本检查失败: {e}")
            return True

    def _simple_version_check(self, sdk_version: str) -> bool:
        def parse_version(v: str) -> tuple:
            parts = v.split(".")
            result = []
            for p in parts:
                try:
                    result.append(int(p.split("-")[0].split("+")[0]))
                except ValueError:
                    result.append(0)
            return tuple(result)

        try:
            current = parse_version(sdk_version)
            if self.min_sdk_version:
                if current < parse_version(self.min_sdk_version):
                    return False
            if self.max_sdk_version:
                if current > parse_version(self.max_sdk_version):
                    return False
            return True
        except Exception:
            return True


def get_sdk_version() -> str:
    try:
        from crawl import __version__
        return __version__
    except ImportError:
        return SDK_VERSION


def check_plugin_compatibility(plugin) -> bool:
    name = getattr(plugin, "name", "unknown")
    version = getattr(plugin, "version", "0.0.0")
    min_sdk = getattr(plugin, "min_sdk_version", None)
    max_sdk = getattr(plugin, "max_sdk_version", None)

    manifest = PluginManifest(
        name=name,
        version=version,
        min_sdk_version=min_sdk,
        max_sdk_version=max_sdk,
    )

    sdk_ver = get_sdk_version()
    compatible = manifest.is_compatible(sdk_ver)

    if not compatible:
        logger.warning(
            f"插件 {name} v{version} 与当前SDK版本 {sdk_ver} 不兼容 "
            f"(要求: {min_sdk} - {max_sdk})"
        )

    return compatible
