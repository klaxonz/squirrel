import logging
import mimetypes

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse

from infrastructure.http.response import error, param_error, success
from infrastructure.site_catalog.icons import resolve_site_icon_path
from infrastructure.site_catalog.login_status import SiteLoginStatusService
from infrastructure.site_catalog.service import SiteCatalogService

from .sites_dependencies import get_catalog_service, get_login_service

logger = logging.getLogger(__name__)
router = APIRouter()

def get_supported_sites(
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
    login_svc: SiteLoginStatusService = Depends(get_login_service),
):
    catalog = catalog_svc.get_merged_site_catalog()
    login_supported_sites = login_svc.get_supported_sites()
    login_supported_sites_lower = {s.lower() for s in login_supported_sites}
    site_names = catalog_svc.merge_site_names(catalog)

    sites_info = []
    for site_name in site_names:
        site_cfg = catalog_svc.build_site_info(site_name, catalog)
        if not site_cfg:
            continue
        site_cfg['supports_login_status'] = site_name.lower() in login_supported_sites_lower
        sites_info.append(site_cfg)

    return success({
        'sites': sites_info,
        'total': len(sites_info),
    })


@router.get('/catalog')
def get_sites_catalog(
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
):
    return success(catalog_svc.get_merged_site_catalog())


@router.put('/catalog')
def update_sites_catalog(
    payload: dict = Body(...),
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
):
    sites_payload = payload.get('sites') if isinstance(payload, dict) else None
    if not isinstance(sites_payload, dict):
        return param_error('sites must be a dict')

    try:
        catalog = catalog_svc.save_site_overrides(sites_payload)
        return success(catalog, msg='site config updated')
    except ValueError as exc:
        return param_error(str(exc))
    except Exception:
        logger.exception('Failed to update site catalog')
        return error('failed to save site config')


@router.get('/{site_name}/icon', include_in_schema=False)
def get_site_icon(site_name: str):
    icon_path = resolve_site_icon_path(site_name)
    if icon_path is None:
        raise HTTPException(status_code=404, detail=f'No icon asset for site: {site_name}')
    media_type, _ = mimetypes.guess_type(icon_path.name)
    return FileResponse(path=icon_path, media_type=media_type or 'application/octet-stream')
