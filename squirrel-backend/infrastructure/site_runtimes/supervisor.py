from __future__ import annotations

import json
import logging
import subprocess
import threading
import urllib.error
from collections.abc import Sequence
from pathlib import Path

from crawl import SiteRuntimeError, SiteRuntimeInvokeRequest, SiteRuntimeInvokeResponse

from .audit import SiteRuntimeAuditWriter
from .health import SiteRuntimeHealthChecker, SiteRuntimeHealthCheckError, to_health_snapshot
from .invocation import SiteRuntimeInvocationClient
from .models import (
    SiteRuntimeHandle,
    SiteRuntimeHealthSnapshot,
    SiteRuntimeRecord,
    SiteRuntimeState,
    SiteRuntimeTarget,
    utcnow_iso,
)
from .process_launcher import SiteRuntimeProcessLauncher
from .transport import SiteRuntimeTransportClient

logger = logging.getLogger(__name__)


class SiteRuntimeSupervisorError(RuntimeError):
    """Raised when runtime supervision fails."""


class SiteRuntimeSupervisor:
    """Own and manage site runtime subprocesses plus transport requests to them.

    This class is the single owner of all runtime state (handles, records,
    subprocesses, log streams, expiry timers). Lifecycle methods that used to
    live in a separate ``SiteRuntimeLifecycle`` module have been folded in so
    there is one source of truth and no callback / shared-mutable-state loops.
    """

    def __init__(
        self,
        *,
        backend_root: Path | None = None,
        audit_writer: SiteRuntimeAuditWriter | None = None,
        transport_client: SiteRuntimeTransportClient | None = None,
        health_checker: SiteRuntimeHealthChecker | None = None,
        process_launcher: SiteRuntimeProcessLauncher | None = None,
    ) -> None:
        self._handles: dict[str, SiteRuntimeHandle] = {}
        self._records: dict[str, SiteRuntimeRecord] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._log_streams: dict[str, tuple[object, object]] = {}
        self._runtime_timers: dict[str, threading.Timer] = {}
        self._backend_root = backend_root or Path(__file__).resolve().parent.parent.parent
        self._audit_writer = audit_writer or SiteRuntimeAuditWriter(self._backend_root)
        self._transport_client = transport_client or SiteRuntimeTransportClient()
        self._health_checker = health_checker or SiteRuntimeHealthChecker(self._transport_client)
        self._process_launcher = process_launcher or SiteRuntimeProcessLauncher(
            self._backend_root, self._audit_writer
        )
        self._invocation_client = SiteRuntimeInvocationClient(
            self._transport_client,
            self._health_checker,
            self._audit_writer,
            self.mark_failed,
        )

    def _key(self, runtime_id: str, version: str) -> str:
        return f"{runtime_id}:{version}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def register_placeholder(self, record: SiteRuntimeRecord) -> SiteRuntimeHandle:
        key = self._key(record.runtime_id, record.version)
        handle = SiteRuntimeHandle(
            runtime_id=record.runtime_id,
            version=record.version,
            state=SiteRuntimeState.STOPPED,
        )
        self._handles[key] = handle
        self._records[key] = record
        return handle

    def start_runtime(
        self,
        record: SiteRuntimeRecord,
        command: Sequence[str] | None = None,
        cwd: Path | None = None,
        endpoint: str | None = None,
    ) -> SiteRuntimeHandle:
        key = self._key(record.runtime_id, record.version)
        self._records[key] = record
        handle = self._handles.get(key) or self.register_placeholder(record)
        handle.state = SiteRuntimeState.STARTING
        handle.started_at = utcnow_iso()
        handle.endpoint = endpoint
        handle.last_error = None

        host = '127.0.0.1'
        port = self._process_launcher.pick_port()
        runtime_endpoint = endpoint or f'http://{host}:{port}'
        process_command = list(command) if command else self._process_launcher.build_runtime_command(record, host, port)
        startup_timeout_ms = int(
            ((record.manifest or {}).get('health_policy') or {}).get('startup_timeout_ms')
            or 10000,
        )
        process_cwd = cwd or self._process_launcher.resolve_runtime_cwd(record)
        process_env = self._process_launcher.build_process_env(record)
        stdout_handle, stderr_handle = self._process_launcher.open_log_streams(record)
        self._audit_writer.append_event(
            record,
            event='runtime_starting',
            details={
                'cwd': str(process_cwd),
                'command': process_command,
            },
        )

        process = self._process_launcher.launch(
            record,
            process_command,
            process_cwd,
            process_env,
            stdout_handle,
            stderr_handle,
        )
        self._log_streams[key] = (stdout_handle, stderr_handle)
        self._processes[key] = process
        handle.process_id = process.pid
        handle.endpoint = runtime_endpoint

        try:
            health = self._wait_for_runtime(process, runtime_endpoint, startup_timeout_ms)
            handle.health = to_health_snapshot(record.runtime_id, health)
            if not health.healthy:
                handle.state = SiteRuntimeState.FAILED
                handle.last_error = health.message
                self._audit_writer.append_event(record, event='runtime_unhealthy', details={'message': health.message})
            else:
                handle.state = SiteRuntimeState.RUNNING
                self._audit_writer.append_event(
                    record,
                    event='runtime_started',
                    details={
                        'pid': process.pid,
                        'endpoint': runtime_endpoint,
                    },
                )
                self._schedule_runtime_expiry(key, record)
        except Exception as exc:
            handle.state = SiteRuntimeState.FAILED
            handle.last_error = str(exc)
            self._audit_writer.append_event(record, event='runtime_failed', details={'reason': str(exc)})
            self.stop_runtime(record.runtime_id, record.version)
            raise

        self._handles[key] = handle
        return handle

    def drain_runtime(self, runtime_id: str, version: str) -> SiteRuntimeHandle | None:
        handle = self._handles.get(self._key(runtime_id, version))
        if handle is None:
            return None
        handle.state = SiteRuntimeState.DRAINING
        handle.drained_at = utcnow_iso()
        return handle

    def stop_runtime(self, runtime_id: str, version: str) -> SiteRuntimeHandle | None:
        key = self._key(runtime_id, version)
        handle = self._handles.get(key)
        process = self._processes.pop(key, None)
        self._cancel_runtime_timer(key)
        if process is not None and process.poll() is None:
            if handle and handle.endpoint:
                try:
                    self._transport_client.request_json(handle.endpoint, '/stop', payload={}, timeout=2.0)
                except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
                    logger.warning(
                        'Site runtime stop request failed: runtime_id=%s, version=%s, error=%s',
                        runtime_id,
                        version,
                        exc,
                    )
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        log_streams = self._log_streams.pop(key, None)
        if log_streams is not None:
            for stream in log_streams:
                try:
                    stream.close()
                except OSError as exc:
                    logger.warning(
                        'Site runtime log stream close failed: runtime_id=%s, version=%s, error=%s',
                        runtime_id,
                        version,
                        exc,
                    )
        if handle is None:
            return None
        handle.state = SiteRuntimeState.STOPPED
        record = self._records.get(key)
        if record is not None:
            self._audit_writer.append_event(record, event='runtime_stopped', details={})
        return handle

    def heartbeat(self, runtime_id: str, version: str, health: SiteRuntimeHealthSnapshot) -> None:
        key = self._key(runtime_id, version)
        handle = self._handles.get(key)
        if handle is None:
            raise SiteRuntimeSupervisorError(f"Runtime handle not found: {key}")
        handle.health = health
        if not health.healthy:
            handle.state = SiteRuntimeState.FAILED
            handle.last_error = health.message

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

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _schedule_runtime_expiry(self, key: str, record: SiteRuntimeRecord) -> None:
        runtime_policy = self._process_launcher.runtime_policy(record)
        max_runtime_seconds = runtime_policy.get('max_runtime_seconds')
        if max_runtime_seconds is None:
            return

        def _expire() -> None:
            self._audit_writer.append_event(
                record,
                event='runtime_expired',
                details={'max_runtime_seconds': max_runtime_seconds},
            )
            self.mark_failed(record.runtime_id, record.version, 'runtime_expired')
            self.stop_runtime(record.runtime_id, record.version)

        timer = threading.Timer(float(max_runtime_seconds), _expire)
        timer.daemon = True
        timer.start()
        self._runtime_timers[key] = timer

    def _cancel_runtime_timer(self, key: str) -> None:
        timer = self._runtime_timers.pop(key, None)
        if timer is not None:
            timer.cancel()

    def _wait_for_runtime(
        self,
        process: subprocess.Popen,
        endpoint: str,
        startup_timeout_ms: int,
    ):
        try:
            return self._health_checker.wait_for_runtime(process, endpoint, startup_timeout_ms)
        except SiteRuntimeHealthCheckError as exc:
            raise SiteRuntimeSupervisorError(str(exc)) from exc
