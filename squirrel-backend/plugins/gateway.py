from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Protocol

from crawl import (
    PluginInvokeRequest,
    PluginInvokeResponse,
    PluginRuntimeError,
)

from .models import PluginCapabilityRegistration, PluginRoutingTarget
from .runtime_models import PluginManifest


class PluginInvocationClient(Protocol):
    """Transport abstraction between host and plugin runtimes."""

    def invoke(self, target: PluginRoutingTarget, request: PluginInvokeRequest) -> PluginInvokeResponse:
        ...


class PluginGateway:
    """Route capability requests to runtime targets."""

    def __init__(self, invocation_client: Optional[PluginInvocationClient] = None) -> None:
        self._invocation_client = invocation_client
        self._registrations: List[PluginCapabilityRegistration] = []

    def register_manifest(self, plugin_id: str, version: str, manifest: PluginManifest) -> None:
        self.unregister_plugin(plugin_id)
        for capability in manifest.capabilities:
            for site in manifest.sites:
                self._registrations.append(
                    PluginCapabilityRegistration(
                        plugin_id=plugin_id,
                        version=version,
                        capability=capability.name,
                        site_name=site.site_name,
                        domains=list(site.domains),
                        metadata={'display_name': manifest.display_name},
                    )
                )

    def unregister_plugin(self, plugin_id: str) -> None:
        self._registrations = [item for item in self._registrations if item.plugin_id != plugin_id]

    def list_registrations(self) -> List[PluginCapabilityRegistration]:
        return list(self._registrations)

    def resolve_route(
        self,
        capability: str,
        site_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[PluginRoutingTarget]:
        normalized_domain = domain.lower() if domain else None
        for registration in self._registrations:
            if registration.capability != capability:
                continue
            if site_name and registration.site_name == site_name:
                return PluginRoutingTarget(
                    plugin_id=registration.plugin_id,
                    version=registration.version,
                    capability=capability,
                    site_name=registration.site_name,
                )
            if normalized_domain and normalized_domain in {item.lower() for item in registration.domains}:
                return PluginRoutingTarget(
                    plugin_id=registration.plugin_id,
                    version=registration.version,
                    capability=capability,
                    site_name=registration.site_name,
                    domain=normalized_domain,
                )
        return None

    def invoke(
        self,
        capability: str,
        payload: Optional[Dict] = None,
        site_name: Optional[str] = None,
        domain: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> PluginInvokeResponse:
        route = self.resolve_route(capability=capability, site_name=site_name, domain=domain)
        if route is None:
            return PluginInvokeResponse(
                request_id='',
                ok=False,
                error=PluginRuntimeError.bad_response(
                    f'No runtime route found for capability: {capability}',
                    details={'capability': capability, 'site_name': site_name, 'domain': domain},
                ),
            )

        request = PluginInvokeRequest(
            request_id=str(uuid.uuid4()),
            capability=capability,
            payload=dict(payload or {}),
            site_name=site_name or route.site_name,
            timeout_ms=timeout_ms,
            metadata={'domain': domain},
        )
        if self._invocation_client is None:
            return PluginInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=PluginRuntimeError.bad_response(
                    'Plugin invocation client is not configured',
                    details={'plugin_id': route.plugin_id, 'capability': capability},
                ),
            )

        response = self._invocation_client.invoke(route, request)
        if not isinstance(response, PluginInvokeResponse):
            return PluginInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=PluginRuntimeError.bad_response(
                    'Plugin runtime returned an invalid response object',
                    details={'plugin_id': route.plugin_id, 'capability': capability},
                ),
            )
        return response
