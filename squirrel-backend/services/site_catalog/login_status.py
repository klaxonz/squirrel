import logging
from datetime import datetime
from typing import Any

from site_runtimes.gateway import SiteRuntimeGateway
from site_runtimes.models import SiteRuntimeSnapshot
from site_runtimes.ports import get_runtime_gateway, get_runtime_snapshot

logger = logging.getLogger(__name__)


class SiteLoginStatusService:
    def __init__(self, gateway: SiteRuntimeGateway | None = None, snapshot: SiteRuntimeSnapshot | None = None):
        self._gateway = gateway or get_runtime_gateway()
        self._snapshot = snapshot or get_runtime_snapshot()

    def get_supported_sites(self) -> set[str]:
        return {
            registration.site_name
            for registration in self._snapshot.registrations
            if registration.capability == 'check_login_status' and registration.site_name
        }

    def test_site_login_status(self, site_name: str) -> dict[str, Any]:
        timestamp = datetime.now().isoformat()
        route = self._gateway.resolve_route('check_login_status', site_name=site_name)
        if route is None:
            return {
                'site_name': site_name,
                'supported': False,
                'logged_in': False,
                'message': 'login check not supported for this site',
                'checked_at': timestamp,
            }

        result = self._gateway.invoke('check_login_status', site_name=site_name)
        if not result.ok or result.error is not None:
            return {
                'site_name': site_name,
                'supported': True,
                'logged_in': False,
                'message': result.error.message if result.error else 'check failed',
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
