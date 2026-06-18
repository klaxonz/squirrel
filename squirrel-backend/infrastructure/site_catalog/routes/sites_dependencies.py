from infrastructure.site_catalog.login_status import SiteLoginStatusService
from infrastructure.site_catalog.service import SiteCatalogService


def get_catalog_service():
    return SiteCatalogService()


def get_login_service() -> SiteLoginStatusService:
    return SiteLoginStatusService()
