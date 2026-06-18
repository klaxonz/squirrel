from fastapi import Request

from infrastructure.site_catalog.login_status import SiteLoginStatusService
from infrastructure.site_catalog.service import SiteCatalogService
from infrastructure.site_runtimes.manager import SiteRuntimeManager


def get_site_runtime_manager(request: Request) -> SiteRuntimeManager:
    return request.app.state.site_runtime_manager


def get_catalog_service():
    return SiteCatalogService()


def get_login_service(request: Request) -> SiteLoginStatusService:
    return SiteLoginStatusService(get_site_runtime_manager(request))
