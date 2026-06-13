from __future__ import annotations

import json
import logging
import subprocess
import threading
import urllib.error
from collections.abc import Callable, MutableMapping, Sequence
from pathlib import Path

from .audit import SiteRuntimeAuditWriter
from .health import SiteRuntimeHealthChecker, SiteRuntimeHealthCheckError, to_health_snapshot
from .models import (
    SiteRuntimeHandle,
    SiteRuntimeHealthSnapshot,
    SiteRuntimeRecord,
    SiteRuntimeState,
    utcnow_iso,
)
from .process_launcher import SiteRuntimeProcessLauncher
from .supervisor_errors import SiteRuntimeSupervisorError
from .transport import SiteRuntimeTransportClient

logger = logging.getLogger(__name__)


class SiteRuntimeLifecycle:
    def __init__(
        self,
        *,
        handles: MutableMapping[str, SiteRuntimeHandle],
        records: MutableMapping[str, SiteRuntimeRecord],
        processes: MutableMapping[str, subprocess.Popen],
        log_streams: MutableMapping[str, tuple[object, object]],
        runtime_timers: MutableMapping[str, threading.Timer],
        audit_writer: SiteRuntimeAuditWriter,
        transport_client: SiteRuntimeTransportClient,
        health_checker: SiteRuntimeHealthChecker,
        process_launcher: SiteRuntimeProcessLauncher,
        mark_failed: Callable[[str, str, str], SiteRuntimeHandle | None],
    ) -> None:
        self._handles = handles
        self._records = records
        self._processes = processes
        self._log_streams = log_streams
        self._runtime_timers = runtime_timers
        self._audit_writer = audit_writer
        self._transport_client = transport_client
        self._health_checker = health_checker
        self._process_launcher = process_launcher
        self._mark_failed = mark_failed

    def _key(self, runtime_id: str, version: str) -> str:
        return f'{runtime_id}:{version}'

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
            self._mark_failed(record.runtime_id, record.version, 'runtime_expired')
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

    def _to_health_snapshot(self, runtime_id: str, health) -> SiteRuntimeHealthSnapshot:
        return to_health_snapshot(runtime_id, health)

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
            handle.health = self._to_health_snapshot(record.runtime_id, health)
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
