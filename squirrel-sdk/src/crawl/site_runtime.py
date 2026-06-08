"""Site runtime helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .exceptions import AuthError, NetworkError, ParseError, PluginError, RateLimitError
from .runtime_errors import SiteRuntimeError
from .runtime_models import (
    SiteRuntimeHealthStatus,
    SiteRuntimeInvokeResponse,
    SiteRuntimeManifest,
)
from .runtime_protocol import SiteRuntime

CapabilityHandler = Callable[[dict[str, Any]], Any]
RuntimeStartHook = Callable[[dict[str, Any] | None], None]
RuntimeStopHook = Callable[[], None]
HealthCheckHook = Callable[[], SiteRuntimeHealthStatus]


class _GeneratedSiteRuntime:
    """Minimal runtime implementation for declarative site runtime packages."""

    def __init__(
        self,
        manifest: SiteRuntimeManifest,
        capability_handlers: dict[str, CapabilityHandler],
        on_start: RuntimeStartHook | None = None,
        on_stop: RuntimeStopHook | None = None,
        health_check: HealthCheckHook | None = None,
    ) -> None:
        self._manifest = manifest
        self._capability_handlers = dict(capability_handlers)
        self._on_start = on_start
        self._on_stop = on_stop
        self._health_check = health_check

    def manifest(self) -> SiteRuntimeManifest:
        return self._manifest

    def start(self, context: dict[str, Any] | None = None) -> None:
        if self._on_start is not None:
            self._on_start(context or {})

    def stop(self) -> None:
        if self._on_stop is not None:
            self._on_stop()

    def health(self) -> SiteRuntimeHealthStatus:
        if self._health_check is not None:
            return self._health_check()
        return SiteRuntimeHealthStatus(healthy=True, status="running")

    def invoke(self, capability: str, payload: dict[str, Any] | None = None) -> SiteRuntimeInvokeResponse:
        request_payload = dict(payload or {})
        request_id = str(request_payload.get("request_id", ""))
        handler = self._capability_handlers.get(capability)
        if handler is None:
            return SiteRuntimeInvokeResponse(
                request_id=request_id,
                ok=False,
                error=SiteRuntimeError.bad_response(
                    f"Unsupported capability: {capability}",
                    details={"capability": capability},
                ),
            )

        try:
            response = handler(request_payload)
            if isinstance(response, SiteRuntimeInvokeResponse):
                return response
            return SiteRuntimeInvokeResponse(request_id=request_id, ok=True, data=response)
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
            # handler boundary: wrap unexpected capability handler errors as crashes
            error = SiteRuntimeError.crashed(
                str(exc),
                details={"exception_type": exc.__class__.__name__},
            )

        return SiteRuntimeInvokeResponse(
            request_id=request_id,
            ok=False,
            error=error,
            retryable=error.retryable,
        )


def create_declarative_site_runtime(
    manifest: SiteRuntimeManifest,
    capability_handlers: dict[str, CapabilityHandler],
    on_start: RuntimeStartHook | None = None,
    on_stop: RuntimeStopHook | None = None,
    health_check: HealthCheckHook | None = None,
) -> SiteRuntime:
    """Create a site runtime object from declarative handlers."""
    return _GeneratedSiteRuntime(
        manifest=manifest,
        capability_handlers=capability_handlers,
        on_start=on_start,
        on_stop=on_stop,
        health_check=health_check,
    )
