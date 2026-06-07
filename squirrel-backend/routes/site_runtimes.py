from fastapi import APIRouter

from common.response import error, success
from services.site_runtime_service import (
    list_site_runtimes as get_site_runtime_list,
)
from services.site_runtime_service import (
    set_enabled_by_name,
)
from site_runtimes.manager import reload_site_runtimes
from utils.redis_client import publish_site_runtime_reload_signal

router = APIRouter(prefix="/api/site-runtimes", tags=["site-runtimes"])


@router.get("/")
def list_site_runtimes():
    return success(get_site_runtime_list())


@router.post("/{name}/enable")
def enable_site_runtime(name: str):
    ok = set_enabled_by_name(name, True)
    if ok:
        publish_site_runtime_reload_signal()
        return success(msg="enabled")
    return error("invalid site runtime name or not found")


@router.post("/{name}/disable")
def disable_site_runtime(name: str):
    ok = set_enabled_by_name(name, False)
    if ok:
        publish_site_runtime_reload_signal()
        return success(msg="disabled")
    return error("invalid site runtime name or not found")


@router.post("/reload")
def reload_all_site_runtimes():
    reload_site_runtimes()
    publish_site_runtime_reload_signal()
    return success(msg="reloaded")
