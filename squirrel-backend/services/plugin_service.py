from __future__ import annotations

from typing import Any, Dict, List

from core.site_config_manager import get_effective_site_catalog
from plugins.manager import get_plugin_manager
from plugins.runtime_models import PluginManifest
from utils.site_icons import build_site_icon_url, resolve_site_icon_path


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
