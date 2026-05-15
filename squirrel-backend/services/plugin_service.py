from __future__ import annotations

import json
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.site_config_manager import get_effective_site_catalog
from plugins.manager import get_plugin_manager
from plugins.runtime_models import PluginManifest
from utils.site_icons import build_site_icon_url, resolve_site_icon_path

InstallResult = Tuple[bool, Optional[Dict[str, Any] | str]]

logger = logging.getLogger(__name__)

RUNTIME_METADATA_FILE = 'plugin-runtime.json'


def _normalize_plugin_site(site_item: Dict[str, Any], catalog: Dict[str, dict]) -> Dict[str, Any]:
    payload = dict(site_item)
    site_name = str(site_item.get('site_name', '')).strip()
    slug = site_name.lower()
    catalog_entry = catalog.get(slug, {})
    icon_url = catalog_entry.get('icon_url')
    if not icon_url and resolve_site_icon_path(site_name):
        icon_url = build_site_icon_url(site_name)
    if icon_url:
        payload['icon_url'] = icon_url
    return payload


def _normalize_plugin_item(record, snapshot, catalog: Dict[str, dict]) -> Dict[str, Any]:
    manifest = PluginManifest.from_dict(record.manifest)
    runtime_handle = next(
        (
            item for item in snapshot.runtimes
            if item.plugin_id == record.plugin_id and item.version == record.version
        ),
        None,
    )

    return {
        'plugin_id': record.plugin_id,
        'display_name': manifest.display_name or record.plugin_id,
        'description': manifest.description,
        'version': record.version,
        'enabled': record.enabled,
        'status': record.status.value,
        'capabilities': [item.to_dict() for item in manifest.capabilities],
        'sites': [_normalize_plugin_site(item.to_dict(), catalog) for item in manifest.sites],
        'permissions': [item.to_dict() for item in manifest.permissions],
        'health': None if runtime_handle is None or runtime_handle.health is None else {
            'healthy': runtime_handle.health.healthy,
            'status': runtime_handle.health.status,
            'message': runtime_handle.health.message,
            'checked_at': runtime_handle.health.checked_at,
            'details': dict(runtime_handle.health.details),
        },
        'active_runtime': None if runtime_handle is None else runtime_handle.to_dict(),
    }


def _read_runtime_metadata(package_path: Path) -> tuple[PluginManifest, str]:
    with zipfile.ZipFile(package_path, 'r') as archive:
        try:
            raw_metadata = archive.read(RUNTIME_METADATA_FILE)
        except KeyError as exc:
            raise ValueError(
                f'Missing {RUNTIME_METADATA_FILE} in plugin package'
            ) from exc

    payload = json.loads(raw_metadata.decode('utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('Invalid runtime metadata payload')

    entrypoint = str(payload.get('entrypoint', '')).strip()
    manifest_payload = payload.get('manifest')
    if not isinstance(manifest_payload, dict):
        raise ValueError('Runtime metadata must include a manifest object')

    return PluginManifest.from_dict(manifest_payload), entrypoint


def install_from_upload(file) -> InstallResult:
    manager = get_plugin_manager()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            package_path = tmp_path / (getattr(file, 'filename', None) or 'plugin.zip')
            file_obj = getattr(file, 'file', None) or file
            try:
                file_obj.seek(0)
            except Exception:
                pass

            with package_path.open('wb') as handle:
                handle.write(file_obj.read())

            manifest, entrypoint = _read_runtime_metadata(package_path)
            record = manager.install_plugin(
                package_path=package_path,
                manifest=manifest,
                entrypoint=entrypoint,
                granted_permissions=[item.name for item in manifest.permissions],
            )
            manager.enable_plugin(record.plugin_id)

            snapshot = manager.get_snapshot()
            refreshed = manager.get_plugin(record.plugin_id)
            if refreshed is None:
                return False, 'plugin was installed but no install record was found'
            return True, _normalize_plugin_item(refreshed, snapshot, get_effective_site_catalog())
    except Exception as exc:
        logger.error('install plugin failed: %s', exc, exc_info=True)
        return False, str(exc)


def list_plugins() -> List[Dict[str, Any]]:
    manager = get_plugin_manager()
    snapshot = manager.get_snapshot()
    catalog = get_effective_site_catalog()
    return [
        _normalize_plugin_item(record, snapshot, catalog)
        for record in snapshot.records
    ]


def set_enabled_by_name(name: str, enabled: bool) -> bool:
    manager = get_plugin_manager()
    record = manager.enable_plugin(name) if enabled else manager.disable_plugin(name)
    return record is not None


def uninstall_by_name(name: str) -> bool:
    manager = get_plugin_manager()
    record = manager.uninstall_plugin(name)
    return record is not None
