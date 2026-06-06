"""Site runtime helpers."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .exceptions import AuthError, NetworkError, ParseError, PluginError, RateLimitError
from .runtime_errors import SiteRuntimeError
from .runtime_models import (
    SiteRuntimeHealthStatus,
    SiteRuntimeInvokeResponse,
    SiteRuntimeManifest,
)
from .runtime_protocol import SiteRuntime


CapabilityHandler = Callable[[Dict[str, Any]], Any]
RuntimeStartHook = Callable[[Optional[Dict[str, Any]]], None]
RuntimeStopHook = Callable[[], None]
HealthCheckHook = Callable[[], SiteRuntimeHealthStatus]


class _GeneratedSiteRuntime:
    """Minimal runtime implementation for declarative site runtime packages."""

    def __init__(
        self,
        manifest: SiteRuntimeManifest,
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

    def manifest(self) -> SiteRuntimeManifest:
        return self._manifest

    def start(self, context: Optional[Dict[str, Any]] = None) -> None:
        if self._on_start is not None:
            self._on_start(context or {})

    def stop(self) -> None:
        if self._on_stop is not None:
            self._on_stop()

    def health(self) -> SiteRuntimeHealthStatus:
        if self._health_check is not None:
            return self._health_check()
        return SiteRuntimeHealthStatus(healthy=True, status='running')

    def invoke(self, capability: str, payload: Optional[Dict[str, Any]] = None) -> SiteRuntimeInvokeResponse:
        request_payload = dict(payload or {})
        request_id = str(request_payload.get('request_id', ''))
        handler = self._capability_handlers.get(capability)
        if handler is None:
            return SiteRuntimeInvokeResponse(
                request_id=request_id,
                ok=False,
                error=SiteRuntimeError.bad_response(
                    f'Unsupported capability: {capability}',
                    details={'capability': capability},
                ),
            )

        try:
            result = handler(request_payload)
            if isinstance(result, SiteRuntimeInvokeResponse):
                return result
            return SiteRuntimeInvokeResponse(request_id=request_id, ok=True, data=result)
        except AuthError as exc:
            error = SiteRuntimeError.auth_required(exc.message, details=exc.context)
        except (NetworkError, RateLimitError) as exc:
            error = SiteRuntimeError.network_error(exc.message, details=exc.context, retryable=exc.retryable)
        except ParseError as exc:
            error = SiteRuntimeError.parse_error(exc.message, details=exc.context)
        except PluginError as exc:
            error = SiteRuntimeError.crashed(exc.message, details=exc.context)
            error.retryable = exc.retryable
        except Exception as exc:
            error = SiteRuntimeError.crashed(
                str(exc),
                details={'exception_type': exc.__class__.__name__},
            )

        return SiteRuntimeInvokeResponse(
            request_id=request_id,
            ok=False,
            error=error,
            retryable=error.retryable,
        )


def create_declarative_site_runtime(
    manifest: SiteRuntimeManifest,
    capability_handlers: Dict[str, CapabilityHandler],
    on_start: Optional[RuntimeStartHook] = None,
    on_stop: Optional[RuntimeStopHook] = None,
    health_check: Optional[HealthCheckHook] = None,
) -> SiteRuntime:
    """Create a site runtime object from declarative handlers."""
    return _GeneratedSiteRuntime(
        manifest=manifest,
        capability_handlers=capability_handlers,
        on_start=on_start,
        on_stop=on_stop,
        health_check=health_check,
    )
