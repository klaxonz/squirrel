from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
CONFIG_FILE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = (CONFIG_FILE.parent / "config" / "plugins.json")

logger = logging.getLogger()


def _read_enabled() -> set[str]:
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as rf:
                data = json.load(rf)
            if isinstance(data, dict) and isinstance(data.get("enabled"), list):
                return {str(n) for n in data["enabled"]}
    except Exception:
        pass
    return set()


def _write_enabled(names: set[str]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as wf:
        json.dump({"enabled": sorted(list(names))}, wf, ensure_ascii=False, indent=2)


class PluginService:
    @staticmethod
    def set_enabled_by_name(name: str, enabled: bool) -> bool:
        if not PluginService._is_valid_name(name):
            return False
        # allow enabling by declared plugin name or by package folder name
        if not (PluginService._plugin_exists(name) or PluginService._declared_plugin_exists(name)):
            return False
        names = _read_enabled()
        if enabled:
            names.add(name)
        else:
            names.discard(name)
        _write_enabled(names)
        return True

    @staticmethod
    def install_from_zip(url: str) -> Tuple[bool, Optional[Dict]]:
        """Download a zip package and extract to plugins_ext; record in DB.
        Expect the zip contains a top-level python package folder.
        """
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ext_dir = base_dir / "plugins_ext"
        ext_dir.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_zip = Path(tmpdir) / "plugin.zip"
                with requests.get(url, timeout=60, stream=True) as r:
                    r.raise_for_status()
                    with open(tmp_zip, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                # extract
                import zipfile
                with zipfile.ZipFile(tmp_zip, 'r') as zf:
                    PluginService._safe_extract(zf, Path(tmpdir))
                # detect top folder
                entries = [e for e in Path(tmpdir).iterdir() if e.is_dir() and e.name != "__MACOSX"]
                if not entries:
                    return False, "Invalid plugin package"
                top = entries[0]
                if not PluginService._is_valid_name(top.name):
                    return False, "Invalid plugin name"
                target = ext_dir / top.name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(top, target)

                result = {
                    "name": top.name,
                    "installed_path": str(target)
                }
                return True, result
        except Exception as e:
            logger.error("install plugin failed: %s", e, exc_info=True)
            return False, str(e)

    @staticmethod
    def uninstall_by_name(name: str) -> bool:
        if not PluginService._is_valid_name(name):
            return False
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        target = base_dir / "plugins_ext" / name
        if not target.exists():
            return False
        try:
            shutil.rmtree(target)
            names = _read_enabled()
            if name in names:
                names.discard(name)
                _write_enabled(names)
            return True
        except Exception as e:
            logger.error("uninstall plugin failed: %s", e, exc_info=True)
            return False

    @staticmethod
    def _safe_extract(zf, dest_dir: Path) -> None:
        """Safely extract zip to dest_dir, preventing path traversal."""
        for member in zf.infolist():
            name = member.filename
            # skip absolute paths
            if os.path.isabs(name):
                continue
            # normalize and ensure within dest_dir
            resolved = (dest_dir / name).resolve()
            if not str(resolved).startswith(str(dest_dir.resolve())):
                continue
            if member.is_dir():
                os.makedirs(resolved, exist_ok=True)
            else:
                os.makedirs(resolved.parent, exist_ok=True)
                with zf.open(member, 'r') as src, open(resolved, 'wb') as out:
                    shutil.copyfileobj(src, out)

    @staticmethod
    def _is_valid_name(name: str) -> bool:
        try:
            import re
            return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name))
        except Exception:
            return False

    @staticmethod
    def _plugin_exists(name: str) -> bool:
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        internal = base_dir / "plugins" / name
        external = base_dir / "plugins_ext" / name
        return internal.exists() or external.exists()

    @staticmethod
    def _declared_plugin_exists(name: str) -> bool:
        # best effort: check if any registered plugin class has this declared name
        try:
            from plugins.registry import all_plugin_classes
            return any(getattr(cls, 'name', None) == name for cls in all_plugin_classes().values())
        except Exception:
            return False


