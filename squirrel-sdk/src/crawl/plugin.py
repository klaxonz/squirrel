"""Plugin helpers for runtime V2 and legacy descriptors."""
from __future__ import annotations

import importlib
import logging
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

from .exceptions import AuthError, NetworkError, ParseError, PluginError, RateLimitError
from .runtime_errors import PluginRuntimeError
from .runtime_models import (
    PluginCapability,
    PluginHealthStatus,
    PluginInvokeResponse,
    PluginManifest,
    PluginPermission,
    PluginSiteManifest,
)
from .runtime_protocol import PluginRuntime

logger = logging.getLogger(__name__)


@dataclass
class PluginDescriptor:
    """Legacy descriptor retained for plugin package migration."""

    name: str
    version: str
    description: str = ''
    domains: List[str] = field(default_factory=list)
    test_url: Optional[str] = None
    components: Dict[str, Type] = field(default_factory=dict)
    display_name: str = ''
    capabilities: List[PluginCapability] = field(default_factory=list)
    permissions: List[PluginPermission] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    health_policy: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_manifest(self) -> PluginManifest:
        """Convert the descriptor into a runtime V2 manifest."""
        features = [capability.name for capability in self.capabilities]
        sites: List[PluginSiteManifest] = []
        if self.domains or self.test_url:
            sites.append(
                PluginSiteManifest(
                    site_name=self.name,
                    domains=list(self.domains),
                    test_url=self.test_url,
                    features=features,
                )
            )

        return PluginManifest(
            plugin_id=self.name,
            version=self.version,
            display_name=self.display_name or self.name,
            description=self.description,
            capabilities=list(self.capabilities),
            sites=sites,
            permissions=list(self.permissions),
            config_schema=dict(self.config_schema),
            health_policy=dict(self.health_policy),
            metadata=dict(self.metadata),
        )


def discover_components(package_name: str) -> Dict[str, Any]:
    """Import conventional plugin component modules for migration helpers."""
    components: Dict[str, Any] = {}

    try:
        importlib.import_module(package_name)
    except ImportError as exc:
        logger.warning('Failed to import package %s: %s', package_name, exc)
        return components

    component_modules = [
        'extractor',
        'handler',
        'subscription',
        'importer',
        'id_extractor',
        'mpd',
        'subtitles',
        'downloader',
        'proxy',
        'config',
        'auth',
    ]

    for module_name in component_modules:
        full_module_name = f'{package_name}.{module_name}'
        try:
            components[module_name] = importlib.import_module(full_module_name)
            logger.debug('Imported component module: %s', full_module_name)
        except ImportError:
            continue

    return components


CapabilityHandler = Callable[[Dict[str, Any]], Any]
RuntimeStartHook = Callable[[Optional[Dict[str, Any]]], None]
RuntimeStopHook = Callable[[], None]
HealthCheckHook = Callable[[], PluginHealthStatus]


class _GeneratedPluginRuntime:
    """Minimal runtime implementation for declarative plugin packages."""

    def __init__(
        self,
        manifest: PluginManifest,
        capability_handlers: Dict[str, CapabilityHandler],
        on_start: Optional[RuntimeStartHook] = None,
        on_stop: Optional[RuntimeStopHook] = None,
        health_check: Optional[HealthCheckHook] = None,
    ) -> None:
        self._manifest = manifest
        self._capability_handlers = dict(capability_handlers)
        self._on_start = on_start
        self._on_stop = on_stop
        self._health_check = health_check

    def manifest(self) -> PluginManifest:
        return self._manifest

    def start(self, context: Optional[Dict[str, Any]] = None) -> None:
        if self._on_start is not None:
            self._on_start(context or {})

    def stop(self) -> None:
        if self._on_stop is not None:
            self._on_stop()

    def health(self) -> PluginHealthStatus:
        if self._health_check is not None:
            return self._health_check()
        return PluginHealthStatus(healthy=True, status='running')

    def invoke(self, capability: str, payload: Optional[Dict[str, Any]] = None) -> PluginInvokeResponse:
        request_payload = dict(payload or {})
        request_id = str(request_payload.get('request_id', ''))
        handler = self._capability_handlers.get(capability)
        if handler is None:
            return PluginInvokeResponse(
                request_id=request_id,
                ok=False,
                error=PluginRuntimeError.bad_response(
                    f'Unsupported capability: {capability}',
                    details={'capability': capability},
                ),
            )

        try:
            result = handler(request_payload)
            if isinstance(result, PluginInvokeResponse):
                return result
            return PluginInvokeResponse(request_id=request_id, ok=True, data=result)
        except PluginRuntimeError as exc:
            return PluginInvokeResponse(
                request_id=request_id,
                ok=False,
                error=exc,
                retryable=exc.retryable,
            )
        except AuthError as exc:
            error = PluginRuntimeError.auth_required(exc.message, details=exc.context)
        except (NetworkError, RateLimitError) as exc:
            error = PluginRuntimeError.network_error(exc.message, details=exc.context, retryable=exc.retryable)
        except ParseError as exc:
            error = PluginRuntimeError.parse_error(exc.message, details=exc.context)
        except PluginError as exc:
            error = PluginRuntimeError.crashed(exc.message, details=exc.context)
            error.retryable = exc.retryable
        except Exception as exc:
            error = PluginRuntimeError.crashed(
                str(exc),
                details={'exception_type': exc.__class__.__name__},
            )

        return PluginInvokeResponse(
            request_id=request_id,
            ok=False,
            error=error,
            retryable=error.retryable,
        )


def create_plugin_runtime(
    manifest: PluginManifest,
    capability_handlers: Dict[str, CapabilityHandler],
    on_start: Optional[RuntimeStartHook] = None,
    on_stop: Optional[RuntimeStopHook] = None,
    health_check: Optional[HealthCheckHook] = None,
) -> PluginRuntime:
    """Create a runtime V2 plugin object from declarative handlers."""
    return _GeneratedPluginRuntime(
        manifest=manifest,
        capability_handlers=capability_handlers,
        on_start=on_start,
        on_stop=on_stop,
        health_check=health_check,
    )


def create_plugin(descriptor: PluginDescriptor, auto_discover: bool = True) -> Type:
    """Create a legacy metadata class without host-side auto-registration."""
    warnings.warn(
        'create_plugin() is a legacy helper. Prefer create_plugin_runtime() for runtime V2 plugins.',
        DeprecationWarning,
        stacklevel=2,
    )

    if auto_discover:
        import inspect

        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_module = frame.f_back.f_globals.get('__name__', '')
            if caller_module:
                discover_components(caller_module.split('.')[0])

    class _GeneratedPlugin:
        name = descriptor.name
        version = descriptor.version
        description = descriptor.description
        manifest = descriptor.to_manifest()

        def on_load(self) -> None:
            logger.debug('Legacy plugin metadata loaded: %s v%s', self.name, self.version)

        def on_app_start(self) -> None:
            return None

        def on_app_stop(self) -> None:
            return None

    _GeneratedPlugin.__name__ = f'{descriptor.name.title()}Plugin'
    _GeneratedPlugin.__qualname__ = _GeneratedPlugin.__name__
    return _GeneratedPlugin


def register_plugin_components(descriptor: PluginDescriptor) -> None:
    """Register legacy in-process components for migration only."""
    from .registries import get_registry_manager

    manager = get_registry_manager()

    for component_type, component_class in descriptor.components.items():
        try:
            if component_type == 'extractor':
                manager.extractor.register(descriptor.name, component_class, descriptor.domains)
            elif component_type == 'subscription':
                manager.subscription.register(descriptor.name, component_class, descriptor.domains)
            elif component_type == 'handler':
                manager.handler.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains,
                )
            elif component_type == 'mpd':
                manager.mpd.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains,
                )
            elif component_type == 'subtitles':
                manager.subtitles.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains,
                )
            elif component_type == 'id_extractor':
                manager.id_extractor.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains,
                )
            elif component_type == 'downloader':
                manager.downloader.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains,
                )
            elif component_type == 'proxy':
                manager.proxy.register(
                    descriptor.domains[0] if descriptor.domains else descriptor.name,
                    component_class,
                    descriptor.domains,
                )
            elif component_type == 'importer':
                manager.importer.register(descriptor.name, component_class)
            elif component_type == 'login_checker':
                manager.login_checker.register(descriptor.name, component_class)

            logger.debug('Registered %s for %s', component_type, descriptor.name)
        except Exception as exc:
            logger.warning('Failed to register %s for %s: %s', component_type, descriptor.name, exc)
