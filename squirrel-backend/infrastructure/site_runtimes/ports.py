from __future__ import annotations

from .gateway import SiteRuntimeGateway
from .manager import get_site_runtime_manager
from .models import SiteRuntimeSnapshot


def get_runtime_gateway() -> SiteRuntimeGateway:
    return get_site_runtime_manager().gateway


def get_runtime_snapshot() -> SiteRuntimeSnapshot:
    return get_site_runtime_manager().get_snapshot()
