from __future__ import annotations

import subprocess
import threading
from collections.abc import Sequence
from pathlib import Path

from crawl import SiteRuntimeError, SiteRuntimeInvokeRequest, SiteRuntimeInvokeResponse

from .audit import SiteRuntimeAuditWriter
from .health import SiteRuntimeHealthChecker
from .invocation import SiteRuntimeInvocationClient
from .lifecycle import SiteRuntimeLifecycle
from .models import (
    SiteRuntimeHandle,
    SiteRuntimeHealthSnapshot,
    SiteRuntimeRecord,
    SiteRuntimeState,
    SiteRuntimeTarget,
)
from .process_launcher import SiteRuntimeProcessLauncher
from .supervisor_errors import SiteRuntimeSupervisorError
from .transport import SiteRuntimeTransportClient


class SiteRuntimeSupervisor:
    """Manage site runtime subprocesses and transport requests to them."""

    def __init__(self) -> None:
        self._handles: dict[str, SiteRuntimeHandle] = {}
        self._records: dict[str, SiteRuntimeRecord] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._log_streams: dict[str, tuple[object, object]] = {}
        self._runtime_timers: dict[str, threading.Timer] = {}
        self._backend_root = Path(__file__).resolve().parent.parent
        self._audit_writer = SiteRuntimeAuditWriter(self._backend_root)
        self._transport_client = SiteRuntimeTransportClient()
        self._health_checker = SiteRuntimeHealthChecker(self._transport_client)
        self._process_launcher = SiteRuntimeProcessLauncher(self._backend_root, self._audit_writer)
        self._lifecycle = SiteRuntimeLifecycle(
            handles=self._handles,
            records=self._records,
            processes=self._processes,
            log_streams=self._log_streams,
            runtime_timers=self._runtime_timers,
            audit_writer=self._audit_writer,
            transport_client=self._transport_client,
            health_checker=self._health_checker,
            process_launcher=self._process_launcher,
            mark_failed=self.mark_failed,
        )
        self._invocation_client = SiteRuntimeInvocationClient(
            self._transport_client,
            self._health_checker,
            self._audit_writer,
            self.mark_failed,
        )

    def _key(self, runtime_id: str, version: str) -> str:
        return f"{runtime_id}:{version}"

    def register_placeholder(self, record: SiteRuntimeRecord) -> SiteRuntimeHandle:
        return self._lifecycle.register_placeholder(record)

    def start_runtime(
        self,
        record: SiteRuntimeRecord,
        command: Sequence[str] | None = None,
        cwd: Path | None = None,
        endpoint: str | None = None,
    ) -> SiteRuntimeHandle:
        return self._lifecycle.start_runtime(record, command=command, cwd=cwd, endpoint=endpoint)

    def heartbeat(self, runtime_id: str, version: str, health: SiteRuntimeHealthSnapshot) -> None:
        key = self._key(runtime_id, version)
        handle = self._handles.get(key)
        if handle is None:
            raise SiteRuntimeSupervisorError(f"Runtime handle not found: {key}")
        handle.health = health
        if not health.healthy:
            handle.state = SiteRuntimeState.FAILED
            handle.last_error = health.message

    def drain_runtime(self, runtime_id: str, version: str) -> SiteRuntimeHandle | None:
        return self._lifecycle.drain_runtime(runtime_id, version)

    def stop_runtime(self, runtime_id: str, version: str) -> SiteRuntimeHandle | None:
        return self._lifecycle.stop_runtime(runtime_id, version)

    def mark_failed(self, runtime_id: str, version: str, message: str) -> SiteRuntimeHandle | None:
        key = self._key(runtime_id, version)
        handle = self._handles.get(key)
        if handle is None:
            return None
        handle.state = SiteRuntimeState.FAILED
        handle.last_error = message
        record = self._records.get(key)
        if record is not None:
            self._audit_writer.append_event(record, event="runtime_marked_failed", details={"reason": message})
        return handle

    def get_handle(self, runtime_id: str, version: str) -> SiteRuntimeHandle | None:
        return self._handles.get(self._key(runtime_id, version))

    def list_handles(self) -> list[SiteRuntimeHandle]:
        return list(self._handles.values())

    def invoke(self, target: SiteRuntimeTarget, request: SiteRuntimeInvokeRequest) -> SiteRuntimeInvokeResponse:
        key = self._key(target.runtime_id, target.version)
        handle = self._handles.get(key)
        if handle is None or not handle.endpoint:
            return SiteRuntimeInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=SiteRuntimeError.bad_response(
                    "Site runtime is not running",
                    details={"runtime_id": target.runtime_id, "version": target.version},
                ),
            )

        return self._invocation_client.invoke(target, request, handle, self._records.get(key))


