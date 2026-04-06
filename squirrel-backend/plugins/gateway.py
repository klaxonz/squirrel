from __future__ import annotations

import logging
import uuid
from typing import Callable, Dict, List, Optional, Protocol

from crawl import (
    PluginInvokeRequest,
    PluginInvokeResponse,
    PluginRuntimeError,
)

from .models import PluginCapabilityRegistration, PluginRoutingTarget
from .runtime_models import PluginManifest

logger = logging.getLogger(__name__)


class PluginInvocationClient(Protocol):
    """Transport abstraction between host and plugin runtimes."""

    def invoke(self, target: PluginRoutingTarget, request: PluginInvokeRequest) -> PluginInvokeResponse:
        ...


class PluginGateway:
    """Route capability requests to runtime targets."""

    def __init__(
        self,
        invocation_client: Optional[PluginInvocationClient] = None,
        registration_refresh: Optional[Callable[[], None]] = None,
    ) -> None:
        self._invocation_client = invocation_client
        self._registration_refresh = registration_refresh
        self._registrations: List[PluginCapabilityRegistration] = []

    def set_registration_refresh(self, callback: Optional[Callable[[], None]]) -> None:
        self._registration_refresh = callback

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
                        timeout_ms=capability.timeout_ms,
                        metadata={'display_name': manifest.display_name},
                    )
                )

    def unregister_plugin(self, plugin_id: str) -> None:
        self._registrations = [item for item in self._registrations if item.plugin_id != plugin_id]

    def list_registrations(self) -> List[PluginCapabilityRegistration]:
        return list(self._registrations)

    def _find_registration(
        self,
        capability: str,
        site_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[PluginCapabilityRegistration]:
        normalized_domain = domain.lower() if domain else None
        for registration in self._registrations:
            if registration.capability != capability:
                continue
            if site_name and registration.site_name == site_name:
                return registration
            if normalized_domain and normalized_domain in {item.lower() for item in registration.domains}:
                return registration
        return None

    def _resolve_registration(
        self,
        capability: str,
        site_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[PluginCapabilityRegistration]:
        registration = self._find_registration(capability=capability, site_name=site_name, domain=domain)
        if registration is not None or self._registration_refresh is None:
            return registration

        try:
            self._registration_refresh()
        except Exception:
            logger.warning(
                'Plugin registration refresh failed while resolving capability=%s site_name=%s domain=%s',
                capability,
                site_name,
                domain,
                exc_info=True,
            )
            return None

        return self._find_registration(capability=capability, site_name=site_name, domain=domain)

    def resolve_route(
        self,
        capability: str,
        site_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[PluginRoutingTarget]:
        registration = self._resolve_registration(capability=capability, site_name=site_name, domain=domain)
        if registration is None:
            return None
        return PluginRoutingTarget(
            plugin_id=registration.plugin_id,
            version=registration.version,
            capability=capability,
            site_name=registration.site_name,
            domain=domain.lower() if domain else None,
        )

    def invoke(
        self,
        capability: str,
        payload: Optional[Dict] = None,
        site_name: Optional[str] = None,
        domain: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> PluginInvokeResponse:
        registration = self._resolve_registration(capability=capability, site_name=site_name, domain=domain)
        if registration is None:
            return PluginInvokeResponse(
                request_id='',
                ok=False,
                error=PluginRuntimeError.bad_response(
                    f'No runtime route found for capability: {capability}',
                    details={'capability': capability, 'site_name': site_name, 'domain': domain},
                ),
            )
        route = PluginRoutingTarget(
            plugin_id=registration.plugin_id,
            version=registration.version,
            capability=capability,
            site_name=registration.site_name,
            domain=domain.lower() if domain else None,
        )
        effective_timeout_ms = timeout_ms if timeout_ms is not None else registration.timeout_ms

        request = PluginInvokeRequest(
            request_id=str(uuid.uuid4()),
            capability=capability,
            payload=dict(payload or {}),
            site_name=site_name or route.site_name,
            timeout_ms=effective_timeout_ms,
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
