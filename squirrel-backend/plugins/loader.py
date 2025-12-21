from __future__ import annotations

import importlib
import json
import logging
import os
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .registry import instantiate_all, reset_registry
from .manifest import check_plugin_compatibility

logger = logging.getLogger(__name__)


@dataclass
class PluginConfig:
    """插件配置"""
    name: str
    enabled: bool = True
    priority: int = 0
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginsConfig:
    """插件配置集合"""
    plugins: Dict[str, PluginConfig] = field(default_factory=dict)

    def is_enabled(self, name: str) -> bool:
        if not self.plugins:
            return True
        cfg = self.plugins.get(name)
        return cfg.enabled if cfg else False

    def get_priority(self, name: str) -> int:
        cfg = self.plugins.get(name)
        return cfg.priority if cfg else 0

    def get_config(self, name: str) -> Dict[str, Any]:
        cfg = self.plugins.get(name)
        return cfg.config if cfg else {}

    def get_enabled_names(self) -> Optional[Set[str]]:
        if not self.plugins:
            return None
        return {name for name, cfg in self.plugins.items() if cfg.enabled}


_loaded_plugins = []  # type: ignore[var-annotated]
_loaded_external_modules: Set[str] = set()
_plugins_config: Optional[PluginsConfig] = None


def _load_plugins_config(base_dir: Path) -> PluginsConfig:
    global _plugins_config
    try:
        cfg_path = base_dir / "config" / "plugins.json"
        if not cfg_path.exists():
            _plugins_config = PluginsConfig()
            return _plugins_config

        with open(cfg_path, "r", encoding="utf-8") as rf:
            data = json.load(rf)

        if not isinstance(data, dict):
            _plugins_config = PluginsConfig()
            return _plugins_config

        # 新格式: {"plugins": {"name": {"enabled": true, "priority": 10, "config": {}}}}
        if "plugins" in data and isinstance(data["plugins"], dict):
            plugins = {}
            for name, cfg in data["plugins"].items():
                if isinstance(cfg, dict):
                    plugins[name] = PluginConfig(
                        name=name,
                        enabled=cfg.get("enabled", True),
                        priority=cfg.get("priority", 0),
                        config=cfg.get("config", {})
                    )
                else:
                    plugins[name] = PluginConfig(name=name, enabled=bool(cfg))
            _plugins_config = PluginsConfig(plugins=plugins)
            return _plugins_config

        # 旧格式兼容: {"enabled": ["plugin1", "plugin2"]}
        names = data.get("enabled", [])
        if isinstance(names, list):
            plugins = {str(n).strip(): PluginConfig(name=str(n).strip()) for n in names if str(n).strip()}
            _plugins_config = PluginsConfig(plugins=plugins)
            return _plugins_config

        _plugins_config = PluginsConfig()
        return _plugins_config
    except Exception:
        logger.exception("[plugins] failed to read plugins.json")
        _plugins_config = PluginsConfig()
        return _plugins_config


def _read_enabled_plugin_names(base_dir: Path) -> Optional[Set[str]]:
    config = _load_plugins_config(base_dir)
    return config.get_enabled_names()


def _iter_namespace_packages(package_names: List[str]) -> None:
    """Import all submodules in given package names to trigger registrations.

    This performs a shallow scan (no deep recursion) to avoid costly imports.
    """
    for pkg in package_names:
        try:
            mod = importlib.import_module(pkg)
        except (ImportError, ModuleNotFoundError):
            continue

        # iterate submodules
        if hasattr(mod, "__path__"):
            for m in pkgutil.iter_modules(mod.__path__, prefix=f"{pkg}."):
                try:
                    importlib.import_module(m.name)
                except (ImportError, ModuleNotFoundError):
                    logger.debug("[plugins] skip import %s", m.name)


def _extend_sys_path_for_external(external_dir: Path, enabled_names: Optional[Set[str]]) -> List[Path]:
    import sys

    added_roots: List[Path] = []
    if not external_dir.exists():
        return added_roots

    def _ensure(path: Path) -> None:
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.append(path_str)

    children = [p for p in external_dir.iterdir() if p.is_dir()]
    children.sort(key=lambda p: p.name.lower())

    for child in children:
        if enabled_names and child.name not in enabled_names:
            continue
        if not child.is_dir():
            continue
        if child not in added_roots:
            added_roots.append(child)
        src_path = child / "src"
        if src_path.is_dir():
            _ensure(src_path)
            added_roots.append(src_path)
        else:
            _ensure(child)
            added_roots.append(child)

    return added_roots


def _import_external_modules(search_roots: List[Path]) -> None:
    global _loaded_external_modules
    _loaded_external_modules = set()
    for root in search_roots:
        try:
            for module_info in pkgutil.iter_modules([str(root)]):
                name = module_info.name
                try:
                    logger.info("[plugins] importing external module: %s", name)
                    importlib.import_module(name)
                    logger.info("[plugins] imported external module: %s", name)
                    _loaded_external_modules.add(name)
                except (ImportError, ModuleNotFoundError) as e:
                    logger.warning("[plugins] failed to import %s: %s", name, e)
                except Exception as e:
                    logger.error("[plugins] unexpected error importing %s: %s", name, e, exc_info=True)
        except Exception:
            logger.exception("[plugins] failed to scan %s", root)


def init_plugins() -> None:
    """Discover, import and initialize plugins.

    Search order:
    1) Built-in package `plugins_builtin` (optional, for future use)
    2) Project internal `plugins` submodules
    3) External directory at `./plugins_ext`
    """
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # 1) built-in (reserved)
    builtin_pkg = "plugins_builtin"
    # 2) internal
    internal_pkg = "plugins"
    # 3) external folder (non-package)
    external_dir = base_dir / "plugins_ext"

    enabled_names = _read_enabled_plugin_names(base_dir)

    # add external dir to sys.path and import modules if it contains any packages
    external_roots = _extend_sys_path_for_external(external_dir, enabled_names=enabled_names)

    # import packages to trigger registrations
    _iter_namespace_packages([builtin_pkg, internal_pkg])

    # import external packages (non-installed) to trigger registrations
    if external_roots:
        _import_external_modules(external_roots)

    # Instantiate and run lifecycle hooks
    global _loaded_plugins
    candidates = instantiate_all()
    def _matches_enabled(p) -> bool:
        if not enabled_names:
            return True
        try:
            n = getattr(p, "name", None)
            if isinstance(n, str) and n in enabled_names:
                return True
            mod = getattr(p.__class__, "__module__", "")
            root_pkg = str(mod).split(".")[0]
            if root_pkg and root_pkg in enabled_names:
                return True
        except Exception:
            pass
        return False
    _loaded_plugins = [p for p in candidates if _matches_enabled(p)]

    compatible_plugins = []
    for p in _loaded_plugins:
        if check_plugin_compatibility(p):
            compatible_plugins.append(p)
        else:
            name = getattr(p, "name", p.__class__.__name__)
            logger.warning("[plugins] skipping incompatible plugin: %s", name)
    _loaded_plugins = compatible_plugins

    for p in list(_loaded_plugins):
        try:
            if hasattr(p, "on_load"):
                p.on_load()
            logger.info("[plugins] loaded: %s v%s", getattr(p, "name", p.__class__.__name__), getattr(p, "version", ""))
        except Exception as e:
            logger.error("[plugins] on_load failed: %s", e)


def app_start() -> None:
    for p in list(_loaded_plugins):
        try:
            if hasattr(p, "on_app_start"):
                p.on_app_start()
        except Exception as e:
            logger.error("[plugins] on_app_start failed: %s", e)


def app_stop() -> None:
    for p in list(_loaded_plugins):
        try:
            if hasattr(p, "on_app_stop"):
                p.on_app_stop()
        except Exception as e:
            logger.error("[plugins] on_app_stop failed: %s", e)


def reload_plugins() -> None:
    """Stop running plugins and re-initialize according to current config."""
    try:
        app_stop()
    except Exception:
        logger.exception("[plugins] error when stopping before reload (ignored)")

    try:
        importlib.invalidate_caches()
    except Exception:
        pass

    try:
        from crawl import reset_all_registries
        reset_all_registries()
    except Exception:
        logger.exception("[plugins] failed to reset crawl registries (ignored)")

    try:
        import sys
        for root_name in list(_loaded_external_modules):
            for k in list(sys.modules.keys()):
                if k == root_name or k.startswith(f"{root_name}."):
                    sys.modules.pop(k, None)
    except Exception:
        logger.exception("[plugins] failed to clear external modules (ignored)")

    reset_registry()
    init_plugins()

    try:
        from core.extraction import reset_factory
        reset_factory()
    except Exception:
        logger.exception("[plugins] failed to reset factory (ignored)")

    try:
        from mq.queue_config import refresh_queue_config
        refresh_queue_config()
    except Exception:
        logger.exception("[plugins] failed to initialize queue config (ignored)")

    try:
        app_start()
    except Exception:
        logger.exception("[plugins] error when starting after reload (ignored)")


def get_plugin_config(name: str) -> Optional[PluginConfig]:
    """获取指定插件的配置"""
    if _plugins_config is None:
        return None
    return _plugins_config.plugins.get(name)


def get_loaded_plugins() -> List:
    """获取已加载的插件列表"""
    return list(_loaded_plugins)



