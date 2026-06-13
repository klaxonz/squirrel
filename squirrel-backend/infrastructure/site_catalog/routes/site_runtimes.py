from fastapi import APIRouter, Depends

from shared_kernel.application.response import error, success
from infrastructure.site_catalog.runtime import SiteRuntimeService
from infrastructure.site_runtimes.manager import reload_site_runtimes
from infrastructure.site_runtimes.signals import publish_site_runtime_reload_signal

router = APIRouter(prefix="/api/site-runtimes", tags=["site-runtimes"])


def get_site_runtime_service() -> SiteRuntimeService:
    return SiteRuntimeService()


@router.get("/")
def list_site_runtimes(svc: SiteRuntimeService = Depends(get_site_runtime_service)):
    return success(svc.list_site_runtimes())


@router.post("/{name}/enable")
def enable_site_runtime(name: str, svc: SiteRuntimeService = Depends(get_site_runtime_service)):
    ok = svc.set_enabled_by_name(name, True)
    if ok:
        publish_site_runtime_reload_signal()
        return success(msg="enabled")
    return error("invalid site runtime name or not found")


@router.post("/{name}/disable")
def disable_site_runtime(name: str, svc: SiteRuntimeService = Depends(get_site_runtime_service)):
    ok = svc.set_enabled_by_name(name, False)
    if ok:
        publish_site_runtime_reload_signal()
        return success(msg="disabled")
    return error("invalid site runtime name or not found")


@router.post("/reload")
def reload_all_site_runtimes():
    reload_site_runtimes()
    publish_site_runtime_reload_signal()
    return success(msg="reloaded")
