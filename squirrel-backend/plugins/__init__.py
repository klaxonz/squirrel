"""Runtime V2 plugin entry points for squirrel-backend."""

from .gateway import PluginGateway
from .manager import (
    PluginManager,
    bootstrap_plugin_runtime,
    get_plugin_manager,
    reload_plugin_runtime,
    shutdown_plugin_runtime,
)
from .paths import PluginPaths, build_plugin_paths
from .store import PluginInstallStore
from .supervisor import PluginRuntimeSupervisor

__all__ = [
    'PluginGateway',
    'PluginInstallStore',
    'PluginManager',
    'PluginPaths',
    'PluginRuntimeSupervisor',
    'bootstrap_plugin_runtime',
    'build_plugin_paths',
    'get_plugin_manager',
    'reload_plugin_runtime',
    'shutdown_plugin_runtime',
]


