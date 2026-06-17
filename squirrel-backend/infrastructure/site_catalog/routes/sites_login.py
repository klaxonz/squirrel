import logging

from fastapi import APIRouter, Depends

from infrastructure.http.response import param_error, success
from infrastructure.site_catalog.login_status import SiteLoginStatusService
from infrastructure.site_catalog.service import SiteCatalogService

from .sites_dependencies import get_catalog_service, get_login_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/{site_name}/login-status')
def get_site_login_status(
    site_name: str,
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
    login_svc: SiteLoginStatusService = Depends(get_login_service),
):
    catalog = catalog_svc.get_merged_site_catalog()
    site_info = catalog_svc.build_site_info(site_name, catalog)
    if not site_info:
        return param_error(f'Unsupported site: {site_name}')

    status = login_svc.test_site_login_status(site_name)

    if site_name.lower() == 'youtube':
        try:
            from infrastructure.site_catalog.youtube_oauth import get_oauth_state
            oauth_state = get_oauth_state()
            status['oauth_status'] = oauth_state.status
            status['oauth_account'] = {
                'name': oauth_state.account.name if oauth_state.account else None,
                'email': oauth_state.account.email if oauth_state.account else None,
                'avatar': oauth_state.account.avatar if oauth_state.account else None,
            } if oauth_state.account else None
        except Exception:
            logger.warning('Failed to fetch YouTube OAuth status', exc_info=True)

    return success(status)
