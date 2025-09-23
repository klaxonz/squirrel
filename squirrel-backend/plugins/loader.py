from __future__ import annotations

import importlib
import json
import logging
import os
import pkgutil
from pathlib import Path
from typing import List, Optional, Set

from .registry import instantiate_all

logger = logging.getLogger()


_loaded_plugins = []  # type: ignore[var-annotated]


def _iter_namespace_packages(package_names: List[str]) -> None:
    """Import all submodules in given package names to trigger registrations.

    This performs a shallow scan (no deep recursion) to avoid costly imports.
    """
    for pkg in package_names:
        try:
            mod = importlib.import_module(pkg)
        except Exception:
            continue

        # iterate submodules
        if hasattr(mod, "__path__"):
            for m in pkgutil.iter_modules(mod.__path__, prefix=f"{pkg}."):
                try:
                    importlib.import_module(m.name)
                except Exception:
                    logger.debug("[plugins] skip import %s", m.name)


def _extend_sys_path_for_external(external_dir: Path) -> None:
    import sys
    if not external_dir.exists():
        return
    path_str = str(external_dir)
    if path_str not in sys.path:
        sys.path.append(path_str)


def init_plugins() -> None:
    """Discover, import and initialize plugins.

    Search order:
    1) Built-in package `plugins_builtin` (optional, for future use)
    2) Project internal `plugins` submodules
    3) External directory at `./plugins_ext` (optional, editable plugins)
    """
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # 1) built-in (reserved)
    builtin_pkg = "plugins_builtin"
    # 2) internal
    internal_pkg = "plugins"
    # 3) external folder (non-package)
    external_dir = base_dir / "plugins_ext"

    # add external dir to sys.path and import modules if it contains any packages
    _extend_sys_path_for_external(external_dir)

    # import packages to trigger registrations
    _iter_namespace_packages([builtin_pkg, internal_pkg])

    # Instantiate and run lifecycle hooks
    global _loaded_plugins
    # Read enabled plugin names from config file config/plugins.json
    enabled_names: Optional[Set[str]] = None
    try:
        cfg_path = base_dir.parent / "config" / "plugins.json"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as rf:
                data = json.load(rf)
            if isinstance(data, dict):
                names = data.get("enabled", [])
                if isinstance(names, list):
                    enabled_names = {str(n) for n in names}
    except Exception:
        enabled_names = None

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
        import importlib
        importlib.invalidate_caches()
    except Exception:
        pass
    init_plugins()
    try:
        app_start()
    except Exception:
        logger.exception("[plugins] error when starting after reload (ignored)")


