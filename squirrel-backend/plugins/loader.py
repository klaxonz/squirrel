from __future__ import annotations

import importlib
import json
import logging
import os
import pkgutil
from pathlib import Path
from typing import List, Optional, Set

from .registry import instantiate_all, reset_registry
from .manifest import check_plugin_compatibility

logger = logging.getLogger(__name__)


_loaded_plugins = []  # type: ignore[var-annotated]
_loaded_external_modules: Set[str] = set()


def _read_enabled_plugin_names(base_dir: Path) -> Optional[Set[str]]:
    try:
        cfg_path = base_dir.parent / "config" / "plugins.json"
        if not cfg_path.exists():
            return None
        with open(cfg_path, "r", encoding="utf-8") as rf:
            data = json.load(rf)
        if not isinstance(data, dict):
            return None
        names = data.get("enabled", [])
        if not isinstance(names, list):
            return None
        enabled = {str(n).strip() for n in names if str(n).strip()}
        return enabled or None
    except Exception:
        logger.exception("[plugins] failed to read plugins.json")
        return None


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


