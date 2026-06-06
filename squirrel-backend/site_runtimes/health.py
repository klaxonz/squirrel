from __future__ import annotations

import subprocess
import time
from typing import Optional

from crawl import SiteRuntimeHealthStatus

from .models import SiteRuntimeHealthSnapshot, utcnow_iso
from .transport import SiteRuntimeTransportClient


class SiteRuntimeHealthCheckError(RuntimeError):
    pass


class SiteRuntimeHealthChecker:
    def __init__(self, transport_client: SiteRuntimeTransportClient) -> None:
        self._transport_client = transport_client

    def fetch_health(self, endpoint: str, timeout: float = 5.0) -> SiteRuntimeHealthStatus:
        payload = self._transport_client.request_json(endpoint, '/health', timeout=timeout)
        return SiteRuntimeHealthStatus.from_dict(payload)

    def wait_for_runtime(
        self,
        process: subprocess.Popen,
        endpoint: str,
        startup_timeout_ms: int,
    ) -> SiteRuntimeHealthStatus:
        deadline = time.monotonic() + (startup_timeout_ms / 1000)
        last_error: Optional[Exception] = None

        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise SiteRuntimeHealthCheckError('Site runtime exited before becoming healthy')
            try:
                return self.fetch_health(endpoint, timeout=1.0)
            except Exception as exc:
                last_error = exc
                time.sleep(0.1)

        raise SiteRuntimeHealthCheckError(f'Site runtime startup timed out: {last_error}')


def to_health_snapshot(runtime_id: str, health: SiteRuntimeHealthStatus) -> SiteRuntimeHealthSnapshot:
    return SiteRuntimeHealthSnapshot(
        runtime_id=runtime_id,
        healthy=health.healthy,
        status=health.status,
        message=health.message,
        details=dict(health.details),
        checked_at=health.checked_at or utcnow_iso(),
    )
