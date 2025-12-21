"""Plugin descriptor for declarative plugin configuration.

This module provides a declarative way to define plugins, reducing boilerplate code
in plugin __init__.py files.

Usage:
    from crawl.plugin import PluginDescriptor, create_plugin

    # Define plugin descriptor
    plugin = PluginDescriptor(
        name="bilibili",
        version="0.1.0",
        description="Bilibili crawl integration",
        domains=["bilibili.com", "b23.tv"],
    )

    # Create plugin class (auto-registers with backend if available)
    BilibiliPlugin = create_plugin(plugin)
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


@dataclass
class PluginDescriptor:
    """Declarative plugin configuration.

    Attributes:
        name: Plugin name (e.g., "bilibili", "youtube")
        version: Plugin version (e.g., "0.1.0")
        description: Plugin description
        domains: List of supported domains
        test_url: Optional test URL for connectivity testing
        components: Optional dict of component types to classes (auto-discovered if not provided)
    """

    name: str
    version: str
    description: str = ""
    domains: List[str] = field(default_factory=list)
    test_url: Optional[str] = None
    components: Dict[str, Type] = field(default_factory=dict)


def discover_components(package_name: str) -> Dict[str, Any]:
    """Auto-discover plugin components from a package.

    Scans the package for known component types and returns them.

    Args:
        package_name: The package name to scan (e.g., "squirrel_bilibili")

    Returns:
        Dict mapping component type names to their classes/instances
    """
    components = {}

    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        logger.warning(f"Failed to import package {package_name}: {e}")
        return components

    component_modules = [
        "extractor",
        "handler",
        "subscription",
        "importer",
        "id_extractor",
        "mpd",
        "subtitles",
        "downloader",
        "proxy",
        "config",
        "auth",
    ]

    for module_name in component_modules:
        try:
            full_module_name = f"{package_name}.{module_name}"
            importlib.import_module(full_module_name)
            logger.debug(f"Imported component module: {full_module_name}")
        except ImportError:
            pass

    return components


def create_plugin(descriptor: PluginDescriptor, auto_discover: bool = True) -> Type:
    """Create a plugin class from a descriptor.

    This function creates a plugin class that can be registered with the backend
    plugin system. It also auto-discovers and imports component modules.

    Args:
        descriptor: The plugin descriptor
        auto_discover: Whether to auto-discover components from the calling package

    Returns:
        A plugin class that implements the Plugin protocol
    """
    if auto_discover:
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_module = frame.f_back.f_globals.get('__name__', '')
            if caller_module:
                package_name = caller_module.split('.')[0]
                discover_components(package_name)

    class _GeneratedPlugin:
        name = descriptor.name
        version = descriptor.version
        description = descriptor.description

        def on_load(self):
            logger.debug(f"Plugin loaded: {self.name} v{self.version}")

        def on_app_start(self):
            pass

        def on_app_stop(self):
            pass

    _GeneratedPlugin.__name__ = f"{descriptor.name.title()}Plugin"
    _GeneratedPlugin.__qualname__ = _GeneratedPlugin.__name__

    try:
        from plugins.registry import register_plugin
        register_plugin(_GeneratedPlugin)
    except ImportError:
        pass

    return _GeneratedPlugin


def register_plugin_components(descriptor: PluginDescriptor) -> None:
    """Register all components defined in the descriptor.

    This is called automatically by create_plugin if components are provided.

    Args:
        descriptor: The plugin descriptor with components
    """
    from .registries import get_registry_manager

    manager = get_registry_manager()

    for component_type, component_class in descriptor.components.items():
        try:
            if component_type == "extractor":
                manager.extractor.register(
                    descriptor.name, component_class, descriptor.domains
                )
            elif component_type == "subscription":
                manager.subscription.register(
                    descriptor.name, component_class, descriptor.domains
                )
            elif component_type == "handler":
                manager.handler.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains
                )
            elif component_type == "mpd":
                manager.mpd.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains
                )
            elif component_type == "subtitles":
                manager.subtitles.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains
                )
            elif component_type == "id_extractor":
                manager.id_extractor.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains
                )
            elif component_type == "downloader":
                manager.downloader.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains
                )
            elif component_type == "proxy":
                manager.proxy.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains
                )
            elif component_type == "importer":
                manager.importer.register(descriptor.name, component_class)
            elif component_type == "login_checker":
                manager.login_checker.register(descriptor.name, component_class)

            logger.debug(f"Registered {component_type} for {descriptor.name}")

        except Exception as e:
            logger.warning(f"Failed to register {component_type} for {descriptor.name}: {e}")
