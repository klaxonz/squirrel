from __future__ import annotations

import logging
import uuid
from typing import Any

from crawl import (
    SiteRuntimeError,
    SiteRuntimeInvokeRequest,
    SiteRuntimeInvokeResponse,
)

from shared_kernel.infrastructure.trace import get_trace_id

from .models import SiteCapabilityRegistration, SiteRuntimeManifest, SiteRuntimeTarget

logger = logging.getLogger(__name__)


class SiteRuntimeGateway:
    """Route capability requests to runtime targets.

    The gateway only resolves routes from registrations already pushed into it
    via :meth:`register_manifest`. It does *not* perform any side-effecting
    discovery on a cache miss — the owning manager is responsible for warming
    up registrations before requests arrive.
    """

    def __init__(
        self,
        invocation_client: Any,
    ) -> None:
        self._invocation_client = invocation_client
        self._registrations: list[SiteCapabilityRegistration] = []

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
                        metadata={"display_name": manifest.display_name},
                    ),
                )

    def unregister_plugin(self, runtime_id: str) -> None:
        self._registrations = [item for item in self._registrations if item.runtime_id != runtime_id]

    def list_registrations(self) -> list[SiteCapabilityRegistration]:
        return list(self._registrations)

    def _find_registration(
        self,
        capability: str,
        site_name: str | None = None,
        domain: str | None = None,
    ) -> SiteCapabilityRegistration | None:
        normalized_domain = domain.lower() if domain else None
        for registration in self._registrations:
            if registration.capability != capability:
                continue
            if site_name and registration.site_name == site_name:
                return registration
            if normalized_domain and normalized_domain in {item.lower() for item in registration.domains}:
                return registration
        return None

    def resolve_route(
        self,
        capability: str,
        site_name: str | None = None,
        domain: str | None = None,
    ) -> SiteRuntimeTarget | None:
        registration = self._find_registration(capability=capability, site_name=site_name, domain=domain)
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
        payload: dict | None = None,
        site_name: str | None = None,
        domain: str | None = None,
        timeout_ms: int | None = None,
    ) -> SiteRuntimeInvokeResponse:
        registration = self._find_registration(capability=capability, site_name=site_name, domain=domain)
        if registration is None:
            return SiteRuntimeInvokeResponse(
                request_id="",
                ok=False,
                error=SiteRuntimeError.route_not_found(
                    f"No runtime route found for capability: {capability}",
                    details={"capability": capability, "site_name": site_name, "domain": domain},
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
            metadata={"domain": domain},
            trace_id=get_trace_id(),
        )
        return self._invocation_client.invoke(route, request)

