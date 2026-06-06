from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from site_runtimes.gateway import SiteRuntimeGateway
from site_runtimes.models import SiteRuntimeSnapshot
from site_runtimes.ports import get_runtime_gateway, get_runtime_snapshot

logger = logging.getLogger(__name__)


def get_supported_sites(snapshot: SiteRuntimeSnapshot | None = None) -> set[str]:
    snapshot = snapshot or get_runtime_snapshot()
    return {
        registration.site_name
        for registration in snapshot.registrations
        if registration.capability == 'check_login_status' and registration.site_name
    }


def test_site_login_status(
    site_name: str,
    gateway: SiteRuntimeGateway | None = None,
) -> Dict[str, Any]:
    runtime_gateway = gateway or get_runtime_gateway()
    timestamp = datetime.now().isoformat()
    route = runtime_gateway.resolve_route('check_login_status', site_name=site_name)
    if route is None:
        return {
            'site_name': site_name,
            'supported': False,
            'logged_in': False,
            'message': '该站点未提供登录检测实现',
            'checked_at': timestamp,
        }

    result = runtime_gateway.invoke('check_login_status', site_name=site_name)
    if not result.ok or result.error is not None:
        return {
            'site_name': site_name,
            'supported': True,
            'logged_in': False,
            'message': result.error.message if result.error else '检测失败',
            'checked_at': timestamp,
        }

    payload_raw = result.data
    if isinstance(payload_raw, dict):
        payload = dict(payload_raw)
        payload.setdefault('site_name', site_name)
    else:
        payload = {
            'site_name': site_name,
            'logged_in': bool(payload_raw),
        }

    payload.update({
        'site_name': payload.get('site_name', site_name),
        'supported': True,
        'checked_at': timestamp,
    })
    payload.setdefault('message', '')
    payload.setdefault('logged_in', False)
    payload.setdefault('extra', {})
    return payload


