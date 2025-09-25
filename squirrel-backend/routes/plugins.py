from fastapi import APIRouter, File, UploadFile

from services.plugin_service import PluginService
from plugins.loader import reload_plugins
from common.response import success, error, param_error


router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.post("/install")
def install_plugin(file: UploadFile = File(...)):
    filename = (file.filename or "plugin.zip").lower()
    if not filename.endswith(".zip"):
        return param_error("file must be a zip archive")
    ok, data_or_err = PluginService.install_from_upload(file)
    if ok:
        return success(data_or_err, msg="installed")
    return error(data_or_err or "install failed")


@router.get("/")
def list_plugins():
    return success(PluginService.list_plugins())


@router.post("/{name}/enable")
def enable_plugin(name: str):
    ok = PluginService.set_enabled_by_name(name, True)
    if ok:
        return success(msg="enabled")
    return error("invalid plugin name or not found")


@router.post("/{name}/disable")
def disable_plugin(name: str):
    ok = PluginService.set_enabled_by_name(name, False)
    if ok:
        return success(msg="disabled")
    return error("invalid plugin name or not found")


@router.post("/{name}/uninstall")
def uninstall_plugin(name: str):
    ok = PluginService.uninstall_by_name(name)
    if ok:
        return success(msg="uninstalled")
    return error("invalid plugin name or not found, or not in plugins_ext")


@router.post("/reload")
def reload_all_plugins():
    reload_plugins()
    return success(msg="reloaded")


