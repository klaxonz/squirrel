from __future__ import annotations

import logging
import socket
import subprocess
import threading
import time
import urllib.error
from pathlib import Path
from typing import Dict, Optional, Sequence

from crawl import SiteRuntimeInvokeRequest, SiteRuntimeInvokeResponse, SiteRuntimeError

from .audit import SiteRuntimeAuditWriter
from .health import SiteRuntimeHealthChecker, SiteRuntimeHealthCheckError, to_health_snapshot
from .models import (
    SiteRuntimeHealthSnapshot,
    SiteRuntimeRecord,
    SiteRuntimeTarget,
    SiteRuntimeHandle,
    SiteRuntimeState,
    utcnow_iso,
)
from .process_launcher import SiteRuntimeProcessLauncher
from .transport import SiteRuntimeTransportClient

logger = logging.getLogger(__name__)


class SiteRuntimeSupervisorError(RuntimeError):
    """Raised when runtime supervision fails."""


class SiteRuntimeSupervisor:
    """Manage site runtime subprocesses and transport requests to them."""

    def __init__(self) -> None:
        self._handles: Dict[str, SiteRuntimeHandle] = {}
        self._records: Dict[str, SiteRuntimeRecord] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._log_streams: Dict[str, tuple[object, object]] = {}
        self._runtime_timers: Dict[str, threading.Timer] = {}
        self._backend_root = Path(__file__).resolve().parent.parent
        self._audit_writer = SiteRuntimeAuditWriter(self._backend_root)
        self._transport_client = SiteRuntimeTransportClient()
        self._health_checker = SiteRuntimeHealthChecker(self._transport_client)
        self._process_launcher = SiteRuntimeProcessLauncher(self._backend_root, self._audit_writer)

    def _key(self, runtime_id: str, version: str) -> str:
        return f'{runtime_id}:{version}'

    def _build_invoke_details(
        self,
        target: SiteRuntimeTarget,
        request: SiteRuntimeInvokeRequest,
        handle: SiteRuntimeHandle,
        *,
        elapsed_ms: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> dict:
        payload = dict(request.payload or {})
        details = {
            'request_id': request.request_id,
            'task_id': payload.get('task_id'),
            'runtime_id': target.runtime_id,
            'version': target.version,
            'capability': target.capability,
            'site_name': request.site_name or target.site_name,
            'domain': target.domain or request.metadata.get('domain'),
            'url': payload.get('url'),
            'timeout_ms': request.timeout_ms,
            'endpoint': handle.endpoint,
            'process_id': handle.process_id,
        }
        if elapsed_ms is not None:
            details['elapsed_ms'] = elapsed_ms
        if reason is not None:
            details['reason'] = reason
        return details

    @staticmethod
    def _format_invoke_timeout_message(details: dict) -> str:
        return (
            'Site runtime request timed out: '
            f"runtime_id={details.get('runtime_id')}, "
            f"version={details.get('version')}, "
            f"capability={details.get('capability')}, "
            f"request_id={details.get('request_id')}, "
            f"task_id={details.get('task_id')}, "
            f"site_name={details.get('site_name')}, "
            f"domain={details.get('domain')}, "
            f"url={details.get('url')}, "
            f"timeout_ms={details.get('timeout_ms')}, "
            f"elapsed_ms={details.get('elapsed_ms')}, "
            f"endpoint={details.get('endpoint')}, "
            f"process_id={details.get('process_id')}"
        )

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
        command: Optional[Sequence[str]] = None,
        cwd: Optional[Path] = None,
        endpoint: Optional[str] = None,
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
            or 10000
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

    def heartbeat(self, runtime_id: str, version: str, health: SiteRuntimeHealthSnapshot) -> None:
        key = self._key(runtime_id, version)
        handle = self._handles.get(key)
        if handle is None:
            raise SiteRuntimeSupervisorError(f'Runtime handle not found: {key}')
        handle.health = health
        if not health.healthy:
            handle.state = SiteRuntimeState.FAILED
            handle.last_error = health.message

    def drain_runtime(self, runtime_id: str, version: str) -> Optional[SiteRuntimeHandle]:
        handle = self._handles.get(self._key(runtime_id, version))
        if handle is None:
            return None
        handle.state = SiteRuntimeState.DRAINING
        handle.drained_at = utcnow_iso()
        return handle

    def stop_runtime(self, runtime_id: str, version: str) -> Optional[SiteRuntimeHandle]:
        key = self._key(runtime_id, version)
        handle = self._handles.get(key)
        process = self._processes.pop(key, None)
        self._cancel_runtime_timer(key)
        if process is not None and process.poll() is None:
            if handle and handle.endpoint:
                try:
                    self._transport_client.request_json(handle.endpoint, '/stop', payload={}, timeout=2.0)
                except Exception as exc:
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

    def mark_failed(self, runtime_id: str, version: str, message: str) -> Optional[SiteRuntimeHandle]:
        key = self._key(runtime_id, version)
        handle = self._handles.get(key)
        if handle is None:
            return None
        handle.state = SiteRuntimeState.FAILED
        handle.last_error = message
        record = self._records.get(key)
        if record is not None:
            self._audit_writer.append_event(record, event='runtime_marked_failed', details={'reason': message})
        return handle

    def get_handle(self, runtime_id: str, version: str) -> Optional[SiteRuntimeHandle]:
        return self._handles.get(self._key(runtime_id, version))

    def list_handles(self) -> list[SiteRuntimeHandle]:
        return list(self._handles.values())

    def invoke(self, target: SiteRuntimeTarget, request: SiteRuntimeInvokeRequest) -> SiteRuntimeInvokeResponse:
        handle = self._handles.get(self._key(target.runtime_id, target.version))
        if handle is None or not handle.endpoint:
            return SiteRuntimeInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=SiteRuntimeError.bad_response(
                    'Site runtime is not running',
                    details={'runtime_id': target.runtime_id, 'version': target.version},
                ),
            )

        payload = dict(request.payload)
        payload.setdefault('request_id', request.request_id)
        payload.setdefault('site_name', request.site_name)
        payload.setdefault('timeout_ms', request.timeout_ms)
        payload.setdefault('metadata', dict(request.metadata))

        outbound_request = SiteRuntimeInvokeRequest(
            request_id=request.request_id,
            capability=request.capability,
            payload=payload,
            site_name=request.site_name,
            timeout_ms=request.timeout_ms,
            metadata=dict(request.metadata),
        )
        started_at = time.monotonic()
        record = self._records.get(self._key(target.runtime_id, target.version))
        if record is not None:
            self._audit_writer.append_event(
                record,
                event='invoke_started',
                details=self._build_invoke_details(target, request, handle),
            )

        try:
            raw_response = self._transport_client.request_json(
                handle.endpoint,
                '/invoke',
                payload={'request': outbound_request.to_dict()},
                timeout=max((request.timeout_ms or 5000) / 1000, 1.0),
            )
            response = SiteRuntimeInvokeResponse.from_dict(raw_response)
            if handle.endpoint:
                try:
                    health = self._health_checker.fetch_health(handle.endpoint, timeout=1.0)
                    handle.health = self._to_health_snapshot(target.runtime_id, health)
                    handle.state = SiteRuntimeState.RUNNING if health.healthy else SiteRuntimeState.FAILED
                except Exception as exc:
                    logger.warning(
                        'Site runtime health refresh failed after invoke: runtime_id=%s, version=%s, error=%s',
                        target.runtime_id,
                        target.version,
                        exc,
                    )
            if record is not None:
                elapsed_ms = int((time.monotonic() - started_at) * 1000)
                self._audit_writer.append_event(
                    record,
                    event='invoke_completed',
                    details={
                        **self._build_invoke_details(
                            target,
                            request,
                            handle,
                            elapsed_ms=elapsed_ms,
                        ),
                        'ok': response.ok,
                        'error_code': response.error.code if response.error else None,
                    },
                )
            return response
        except (TimeoutError, socket.timeout) as exc:
            self.mark_failed(target.runtime_id, target.version, str(exc))
            details = self._build_invoke_details(
                target,
                request,
                handle,
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
                reason=str(exc),
            )
            if record is not None:
                self._audit_writer.append_event(
                    record,
                    event='invoke_failed',
                    details=details,
                )
            return SiteRuntimeInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=SiteRuntimeError.timeout(
                    self._format_invoke_timeout_message(details),
                    details=details,
                ),
                retryable=True,
            )
        except urllib.error.URLError as exc:
            self.mark_failed(target.runtime_id, target.version, str(exc))
            details = self._build_invoke_details(
                target,
                request,
                handle,
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
                reason=str(exc),
            )
            if record is not None:
                self._audit_writer.append_event(
                    record,
                    event='invoke_failed',
                    details=details,
                )
            return SiteRuntimeInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=SiteRuntimeError.network_error(
                    'Site runtime request failed',
                    details=details,
                ),
            )
        except Exception as exc:
            self.mark_failed(target.runtime_id, target.version, str(exc))
            details = self._build_invoke_details(
                target,
                request,
                handle,
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
                reason=str(exc),
            )
            if record is not None:
                self._audit_writer.append_event(
                    record,
                    event='invoke_failed',
                    details=details,
                )
            return SiteRuntimeInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=SiteRuntimeError.bad_response(
                    'Site runtime returned an invalid response object',
                    details=details,
                ),
            )


