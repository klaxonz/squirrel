"""Runtime V2 plugin entry points for squirrel-backend."""

from .gateway import PluginGateway
from .installer import PluginInstaller
from .manager import (
    PluginManager,
    bootstrap_plugin_runtime,
    get_plugin_manager,
    reload_plugin_runtime,
    shutdown_plugin_runtime,
)
from .store import PluginInstallStore
from .supervisor import PluginRuntimeSupervisor

__all__ = [
    'PluginGateway',
    'PluginInstaller',
    'PluginInstallStore',
    'PluginManager',
    'PluginRuntimeSupervisor',
    'bootstrap_plugin_runtime',
    'get_plugin_manager',
    'reload_plugin_runtime',
    'shutdown_plugin_runtime',
]


