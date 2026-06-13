from services.site_catalog.login_status import SiteLoginStatusService
from services.site_catalog.service import SiteCatalogService


def get_catalog_service():
    return SiteCatalogService()


def get_login_service():
    return SiteLoginStatusService()
