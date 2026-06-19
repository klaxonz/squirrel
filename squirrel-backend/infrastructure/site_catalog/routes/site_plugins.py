from fastapi import APIRouter, Depends

from infrastructure.http.response import error, success
from infrastructure.site_catalog.plugins import SitePluginService

router = APIRouter(prefix='/api/site-runtimes', tags=['site-plugins'])


def get_site_plugin_service() -> SitePluginService:
    return SitePluginService()


@router.get('/')
def list_site_plugins(svc: SitePluginService = Depends(get_site_plugin_service)):
    return success(svc.list_site_plugins())


@router.post('/{name}/enable')
def enable_site_plugin(name: str, svc: SitePluginService = Depends(get_site_plugin_service)):
    ok = svc.set_enabled_by_name(name, True)
    if ok:
        return success(msg='enabled')
    return error('invalid site plugin name or not found')


@router.post('/{name}/disable')
def disable_site_plugin(name: str, svc: SitePluginService = Depends(get_site_plugin_service)):
    ok = svc.set_enabled_by_name(name, False)
    if ok:
        return success(msg='disabled')
    return error('invalid site plugin name or not found')
