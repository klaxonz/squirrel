from __future__ import annotations

import logging
import uuid
from typing import Callable, Dict, List, Optional, Protocol

from crawl import (
    SiteRuntimeInvokeRequest,
    SiteRuntimeInvokeResponse,
    SiteRuntimeError,
)

from .models import SiteCapabilityRegistration, SiteRuntimeTarget
from .runtime_models import SiteRuntimeManifest

logger = logging.getLogger(__name__)


class SiteRuntimeInvocationClient(Protocol):
    """Transport abstraction between host and site runtimes."""

    def invoke(self, target: SiteRuntimeTarget, request: SiteRuntimeInvokeRequest) -> SiteRuntimeInvokeResponse:
        ...


class SiteRuntimeGateway:
    """Route capability requests to runtime targets."""

    def __init__(
        self,
        invocation_client: Optional[SiteRuntimeInvocationClient] = None,
        registration_refresh: Optional[Callable[[], None]] = None,
    ) -> None:
        self._invocation_client = invocation_client
        self._registration_refresh = registration_refresh
        self._registrations: List[SiteCapabilityRegistration] = []

    def set_registration_refresh(self, callback: Optional[Callable[[], None]]) -> None:
        self._registration_refresh = callback

    def register_manifest(self, runtime_id: str, version: str, manifest: SiteRuntimeManifest) -> None:
        self.unregister_plugin(runtime_id)
        for capability in manifest.capabilities:
            for site in manifest.sites:
                self._registrations.append(
                    SiteCapabilityRegistration(
                        runtime_id=runtime_id,
                        version=version,
                        capability=capability.name,
                        site_name=site.site_name,
                        domains=list(site.domains),
                        timeout_ms=capability.timeout_ms,
                        metadata={'display_name': manifest.display_name},
                    )
                )

    def unregister_plugin(self, runtime_id: str) -> None:
        self._registrations = [item for item in self._registrations if item.runtime_id != runtime_id]

    def list_registrations(self) -> List[SiteCapabilityRegistration]:
        return list(self._registrations)

    def _find_registration(
        self,
        capability: str,
        site_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[SiteCapabilityRegistration]:
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
    ) -> Optional[SiteCapabilityRegistration]:
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
    ) -> Optional[SiteRuntimeTarget]:
        registration = self._resolve_registration(capability=capability, site_name=site_name, domain=domain)
        if registration is None:
            return None
        return SiteRuntimeTarget(
            runtime_id=registration.runtime_id,
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
    ) -> SiteRuntimeInvokeResponse:
        registration = self._resolve_registration(capability=capability, site_name=site_name, domain=domain)
        if registration is None:
            return SiteRuntimeInvokeResponse(
                request_id='',
                ok=False,
                error=SiteRuntimeError.route_not_found(
                    f'No runtime route found for capability: {capability}',
                    details={'capability': capability, 'site_name': site_name, 'domain': domain},
                ),
            )
        route = SiteRuntimeTarget(
            runtime_id=registration.runtime_id,
            version=registration.version,
            capability=capability,
            site_name=registration.site_name,
            domain=domain.lower() if domain else None,
        )
        effective_timeout_ms = timeout_ms if timeout_ms is not None else registration.timeout_ms

        request = SiteRuntimeInvokeRequest(
            request_id=str(uuid.uuid4()),
            capability=capability,
            payload=dict(payload or {}),
            site_name=site_name or route.site_name,
            timeout_ms=effective_timeout_ms,
            metadata={'domain': domain},
        )
        if self._invocation_client is None:
            return SiteRuntimeInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=SiteRuntimeError.bad_response(
                    'Plugin invocation client is not configured',
                    details={'runtime_id': route.runtime_id, 'capability': capability},
                ),
            )

        response = self._invocation_client.invoke(route, request)
        if not isinstance(response, SiteRuntimeInvokeResponse):
            return SiteRuntimeInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=SiteRuntimeError.bad_response(
                    'Site runtime returned an invalid response object',
                    details={'runtime_id': route.runtime_id, 'capability': capability},
                ),
            )
        return response


