from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from plugins.manager import get_plugin_manager

logger = logging.getLogger(__name__)


def get_supported_sites() -> set[str]:
    manager = get_plugin_manager()
    return {
        registration.site_name
        for registration in manager.get_snapshot().registrations
        if registration.capability == 'check_login_status' and registration.site_name
    }


def test_site_login_status(site_name: str) -> Dict[str, Any]:
    manager = get_plugin_manager()
    timestamp = datetime.now().isoformat()
    route = manager.gateway.resolve_route('check_login_status', site_name=site_name)
    if route is None:
        return {
            'site_name': site_name,
            'supported': False,
            'logged_in': False,
            'message': '该站点未提供登录检测实现',
            'checked_at': timestamp,
        }

    result = manager.gateway.invoke('check_login_status', site_name=site_name)
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
