from __future__ import annotations

import inspect
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

# Type alias for clarity
InstallResult = Tuple[bool, Optional[Dict]]
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
    def install_from_upload(file) -> InstallResult:
        """Handle uploaded zip file and extract to plugins_ext."""
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ext_dir = base_dir / "plugins_ext"
        ext_dir.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                tmp_zip = tmp_path / "__upload.zip"
                extract_dir = tmp_path / "__extract"
                extract_dir.mkdir(parents=True, exist_ok=True)
                file_obj = getattr(file, "file", None) or file
                try:
                    file_obj.seek(0)
                except Exception:
                    pass
                with open(tmp_zip, "wb") as f:
                    shutil.copyfileobj(file_obj, f)
                import zipfile
                with zipfile.ZipFile(tmp_zip, "r") as zf:
                    namelist = zf.namelist()
                    top_dirs = set()
                    for name in namelist:
                        normalized = name.replace("\\", "/")
                        parts = normalized.split("/")
                        if parts[0] and parts[0] != "__MACOSX":
                            top_dirs.add(parts[0])

                    if not top_dirs:
                        return False, "Invalid plugin package: no top-level directory found"

                    if len(top_dirs) > 1:
                        return False, f"Invalid plugin package: multiple top-level directories: {sorted(top_dirs)}"

                    plugin_name = top_dirs.pop()
                    PluginService._safe_extract(zf, extract_dir)

                # Verify extracted directory
                top = extract_dir / plugin_name
                if not top.exists() or not top.is_dir():
                    # Debug: list what was actually extracted
                    actual_contents = list(extract_dir.iterdir())
                    logger.error(f"Expected '{plugin_name}' but found: {[str(p) for p in actual_contents]}")
                    return False, f"Plugin directory '{plugin_name}' not found after extraction. Found: {[p.name for p in actual_contents]}"
                
                if not PluginService._is_valid_name(plugin_name):
                    return False, f"Invalid plugin name: {plugin_name}"
                
                target = ext_dir / plugin_name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(top, target)

                result = {
                    "name": plugin_name,
                    "installed_path": str(target)
                }
                return True, result
        except Exception as e:
            logger.error("install plugin failed: %s", e, exc_info=True)
            return False, str(e)

    @staticmethod
    def list_plugins() -> List[Dict[str, Any]]:
        from plugins.registry import all_plugin_classes

        enabled_names = _read_enabled()
        items: List[Dict[str, Any]] = []
        registered = all_plugin_classes()
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        internal_root = base_dir / "plugins"
        external_root = base_dir / "plugins_ext"

        for name, cls in registered.items():
            info: Dict[str, Any] = {
                "name": name,
                "version": getattr(cls, "version", None),
                "description": getattr(cls, "description", None),
                "enabled": name in enabled_names,
                "module": getattr(cls, "__module__", None),
                "state": "registered",
            }
            try:
                source_file = inspect.getfile(cls)
                info["path"] = source_file
                resolved = Path(source_file).resolve()
                if internal_root in resolved.parents:
                    info["source"] = "internal"
                elif external_root in resolved.parents:
                    info["source"] = "external"
                else:
                    info["source"] = "package"
            except Exception:
                info["path"] = None
                info["source"] = "unknown"
            items.append(info)

        registered_names = {item["name"] for item in items}
        for missing_name in sorted(enabled_names - registered_names):
            items.append({
                "name": missing_name,
                "version": None,
                "description": None,
                "enabled": True,
                "module": None,
                "path": None,
                "source": "missing",
                "state": "missing",
            })

        return sorted(items, key=lambda x: x["name"].lower())

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
        dest_dir_resolved = dest_dir.resolve()

        normalized_names: list[str] = []
        for member in zf.infolist():
            normalized = member.filename.replace("\\", "/").lstrip("/")
            if normalized:
                normalized_names.append(normalized)

        dir_paths: set[str] = set()
        for name in normalized_names:
            stripped = name.rstrip("/")
            if not stripped:
                continue
            path = PurePosixPath(stripped)
            for parent in path.parents:
                if parent == PurePosixPath("."):
                    continue
                dir_paths.add(f"{parent.as_posix()}/")
            if name.endswith("/"):
                dir_paths.add(name)

        def _ensure_dir(path: Path, member_name: str) -> bool:
            try:
                rel = path.relative_to(dest_dir_resolved)
            except ValueError:
                return False

            current = dest_dir_resolved
            for part in rel.parts:
                current = current / part
                if current.exists():
                    if current.is_dir():
                        continue

                    rel_dir = PurePosixPath(*current.relative_to(dest_dir_resolved).parts).as_posix() + "/"
                    if rel_dir in dir_paths:
                        try:
                            current.unlink()
                        except Exception as e:
                            logger.warning("Skipping %s: cannot replace file with directory: %s", member_name, e)
                            return False
                        current.mkdir(exist_ok=True)
                        continue

                    logger.warning("Skipping %s: path component exists but is not a directory: %s", member_name, str(current))
                    return False

                current.mkdir()
            return True

        for member in zf.infolist():
            name = member.filename.replace("\\", "/").lstrip("/")
            if name.startswith("./"):
                name = name[2:]
            if not name or os.path.isabs(name) or name.startswith("../") or "/../" in name:
                continue

            stripped = name.rstrip("/")
            is_dir = (
                member.is_dir()
                or name.endswith("/")
                or member.filename.endswith("\\")
                or bool(member.external_attr & 0x10)
                or (f"{stripped}/" in dir_paths and member.file_size == 0 and member.compress_size == 0)
            )

            resolved = (dest_dir / stripped).resolve() if is_dir else (dest_dir / name).resolve()
            try:
                resolved.relative_to(dest_dir_resolved)
            except ValueError:
                continue

            if is_dir:
                if _ensure_dir(resolved, name):
                    resolved.mkdir(parents=True, exist_ok=True)
                continue

            if not _ensure_dir(resolved.parent, name):
                continue

            if resolved.exists() and resolved.is_dir():
                logger.warning("Skipping %s: target path exists but is a directory", name)
                continue

            with zf.open(member, "r") as src, open(resolved, "wb") as out:
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


