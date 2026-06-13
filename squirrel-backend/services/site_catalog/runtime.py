from __future__ import annotations

from typing import Any

from core.site_config_manager import get_effective_site_catalog
from site_runtimes.manager import get_site_runtime_manager
from site_runtimes.runtime_models import SiteRuntimeManifest
from utils.site_icons import build_site_icon_url, resolve_site_icon_path


class SiteRuntimeService:
    @staticmethod
    def _normalize_runtime_site(site_item: dict[str, Any], catalog: dict[str, dict]) -> dict[str, Any]:
        payload = dict(site_item)
        site_name = str(site_item.get("site_name", "")).strip()
        slug = site_name.lower()
        catalog_entry = catalog.get(slug, {})
        icon_url = catalog_entry.get("icon_url")
        if not icon_url and resolve_site_icon_path(site_name):
            icon_url = build_site_icon_url(site_name)
        if icon_url:
            payload["icon_url"] = icon_url
        return payload

    @staticmethod
    def _normalize_runtime_item(record, snapshot, catalog: dict[str, dict]) -> dict[str, Any]:
        manifest = SiteRuntimeManifest.from_dict(record.manifest)
        runtime_handle = next(
            (
                item for item in snapshot.runtimes
                if item.runtime_id == record.runtime_id and item.version == record.version
            ),
            None,
        )

        return {
            "runtime_id": record.runtime_id,
            "display_name": manifest.display_name or record.runtime_id,
            "description": manifest.description,
            "version": record.version,
            "enabled": record.enabled,
            "status": record.status.value,
            "capabilities": [item.to_dict() for item in manifest.capabilities],
            "sites": [SiteRuntimeService._normalize_runtime_site(item.to_dict(), catalog) for item in manifest.sites],
            "permissions": [item.to_dict() for item in manifest.permissions],
            "health": None if runtime_handle is None or runtime_handle.health is None else {
                "healthy": runtime_handle.health.healthy,
                "status": runtime_handle.health.status,
                "message": runtime_handle.health.message,
                "checked_at": runtime_handle.health.checked_at,
                "details": dict(runtime_handle.health.details),
            },
            "active_runtime": None if runtime_handle is None else runtime_handle.to_dict(),
        }

    @staticmethod
    def list_site_runtimes() -> dict[str, Any]:
        manager = get_site_runtime_manager()
        snapshot = manager.get_snapshot()
        catalog = get_effective_site_catalog()
        return {
            "items": [
                SiteRuntimeService._normalize_runtime_item(record, snapshot, catalog)
                for record in snapshot.records
            ],
            "discovery_errors": [item.to_dict() for item in snapshot.discovery_errors],
        }

    @staticmethod
    def set_enabled_by_name(name: str, enabled: bool) -> bool:
        manager = get_site_runtime_manager()
        record = manager.enable_site_runtime(name) if enabled else manager.disable_site_runtime(name)
        return record is not None


site_runtime_service = SiteRuntimeService()
list_site_runtimes = site_runtime_service.list_site_runtimes
set_enabled_by_name = site_runtime_service.set_enabled_by_name
