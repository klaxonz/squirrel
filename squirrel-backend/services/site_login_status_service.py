from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from crawl import LoginStatusResult, get_login_checker_registry

logger = logging.getLogger(__name__)


class SiteLoginStatusService:
    @staticmethod
    def get_supported_sites() -> set[str]:
        registry = get_login_checker_registry()
        try:
            return set(registry.get_supported_sites())
        except AttributeError:
            logger.debug("login checker registry missing get_supported_sites")
            return set()

    @staticmethod
    def test(site_name: str) -> Dict[str, Any]:
        registry = get_login_checker_registry()
        checker = registry.get(site_name)
        timestamp = datetime.now(timezone.utc).isoformat()

        if checker is None:
            return {
                "site_name": site_name,
                "supported": False,
                "logged_in": False,
                "message": "该站点未提供登录检测实现",
                "checked_at": timestamp,
            }

        try:
            result = checker()
        except Exception as exc:
            logger.warning("login status checker for %s failed: %s", site_name, exc, exc_info=True)
            return {
                "site_name": site_name,
                "supported": True,
                "logged_in": False,
                "message": f"检测失败: {exc}",
                "checked_at": timestamp,
            }

        if isinstance(result, LoginStatusResult):
            payload = result.to_dict()
        elif isinstance(result, dict):
            payload = dict(result)
            payload.setdefault("site_name", site_name)
        else:
            payload = {
                "site_name": site_name,
                "logged_in": bool(result),
            }

        payload.update({
            "site_name": payload.get("site_name", site_name),
            "supported": True,
            "checked_at": timestamp,
        })
        payload.setdefault("message", "")
        payload.setdefault("logged_in", False)
        payload.setdefault("extra", {})
        return payload
