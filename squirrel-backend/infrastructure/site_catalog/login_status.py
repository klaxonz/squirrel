import logging
from datetime import datetime
from typing import Any

from sites.crawl import SiteError
from infrastructure.site_registry.registry import SiteRegistry, get_site_registry

logger = logging.getLogger(__name__)


class SiteLoginStatusService:
    """Probes login status via first-party site runtimes."""

    def __init__(self, registry: SiteRegistry | None = None):
        self._registry = registry or get_site_registry()

    def get_supported_sites(self) -> set[str]:
        return self._registry.get_supported_sites('check_login_status')

    def test_site_login_status(self, site_name: str) -> dict[str, Any]:
        timestamp = datetime.now().isoformat()
        if not self._registry.has_capability(site_name, 'check_login_status'):
            return {
                'site_name': site_name,
                'supported': False,
                'logged_in': False,
                'message': 'login check not supported for this site',
                'checked_at': timestamp,
            }

        try:
            result = self._registry.get_site_runtime(site_name).check_login_status()
        except SiteError as exc:
            return {
                'site_name': site_name,
                'supported': True,
                'logged_in': False,
                'message': str(exc),
                'checked_at': timestamp,
            }

        payload = dict(result.to_dict())
        payload.setdefault('site_name', site_name)
        payload.update(
            {
                'site_name': payload.get('site_name', site_name),
                'supported': True,
                'checked_at': timestamp,
            }
        )
        payload.setdefault('message', '')
        payload.setdefault('logged_in', False)
        payload.setdefault('extra', {})
        return payload
