from __future__ import annotations

import json
import logging
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Sequence

from crawl import PluginHealthStatus, PluginInvokeRequest, PluginInvokeResponse, PluginRuntimeError

from .models import (
    PluginHealthSnapshot,
    PluginInstallRecord,
    PluginRoutingTarget,
    PluginRuntimeHandle,
    PluginRuntimeState,
    utcnow_iso,
)

logger = logging.getLogger(__name__)


class PluginSupervisorError(RuntimeError):
    """Raised when runtime supervision fails."""


class PluginRuntimeSupervisor:
    """Manage plugin runtime subprocesses and transport requests to them."""

    def __init__(self) -> None:
        self._handles: Dict[str, PluginRuntimeHandle] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._backend_root = Path(__file__).resolve().parent.parent

    def _key(self, plugin_id: str, version: str) -> str:
        return f'{plugin_id}:{version}'

    def _candidate_import_paths(self, record: PluginInstallRecord) -> list[str]:
        candidates: list[Path] = []
        if record.runtime_path:
            candidates.append(Path(record.runtime_path))
        if record.install_path:
            install_path = Path(record.install_path)
            candidates.append(install_path / 'src')
            candidates.append(install_path)

        seen: set[str] = set()
        import_paths: list[str] = []
        for candidate in candidates:
            if not candidate.exists():
                continue
            resolved = str(candidate.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            import_paths.append(resolved)
        return import_paths

    @staticmethod
    def _pick_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('127.0.0.1', 0))
            return int(sock.getsockname()[1])

    def _build_runtime_command(self, record: PluginInstallRecord, host: str, port: int) -> list[str]:
        command = [
            sys.executable,
            '-m',
            'plugins.runtime_bridge',
            '--entrypoint',
            record.entrypoint,
            '--plugin-id',
            record.plugin_id,
            '--version',
            record.version,
            '--host',
            host,
            '--port',
            str(port),
        ]
        for import_path in self._candidate_import_paths(record):
            command.extend(['--import-path', import_path])
        return command

    def _request_json(
        self,
        endpoint: str,
        path: str,
        payload: Optional[dict] = None,
        timeout: float = 5.0,
    ) -> dict:
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            f'{endpoint}{path}',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST' if payload is not None else 'GET',
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            raw_body = response.read().decode('utf-8')
        parsed = json.loads(raw_body or '{}')
        return parsed if isinstance(parsed, dict) else {}

    def _fetch_health(self, endpoint: str, timeout: float = 5.0) -> PluginHealthStatus:
        payload = self._request_json(endpoint, '/health', timeout=timeout)
        return PluginHealthStatus.from_dict(payload)

    def _wait_for_runtime(
        self,
        process: subprocess.Popen,
        endpoint: str,
        startup_timeout_ms: int,
    ) -> PluginHealthStatus:
        deadline = time.monotonic() + (startup_timeout_ms / 1000)
        last_error: Optional[Exception] = None

        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise PluginSupervisorError('Plugin runtime exited before becoming healthy')
            try:
                return self._fetch_health(endpoint, timeout=1.0)
            except Exception as exc:
                last_error = exc
                time.sleep(0.1)

        raise PluginSupervisorError(f'Plugin runtime startup timed out: {last_error}')

    def _to_health_snapshot(self, plugin_id: str, health: PluginHealthStatus) -> PluginHealthSnapshot:
        return PluginHealthSnapshot(
            plugin_id=plugin_id,
            healthy=health.healthy,
            status=health.status,
            message=health.message,
            details=dict(health.details),
            checked_at=health.checked_at or utcnow_iso(),
        )

    def register_placeholder(self, record: PluginInstallRecord) -> PluginRuntimeHandle:
        handle = PluginRuntimeHandle(
            plugin_id=record.plugin_id,
            version=record.version,
            state=PluginRuntimeState.STOPPED,
        )
        self._handles[self._key(record.plugin_id, record.version)] = handle
        return handle

    def start_runtime(
        self,
        record: PluginInstallRecord,
        command: Optional[Sequence[str]] = None,
        cwd: Optional[Path] = None,
        endpoint: Optional[str] = None,
    ) -> PluginRuntimeHandle:
        key = self._key(record.plugin_id, record.version)
        handle = self._handles.get(key) or self.register_placeholder(record)
        handle.state = PluginRuntimeState.STARTING
        handle.started_at = utcnow_iso()
        handle.endpoint = endpoint
        handle.last_error = None

        host = '127.0.0.1'
        port = self._pick_port()
        runtime_endpoint = endpoint or f'http://{host}:{port}'
        process_command = list(command) if command else self._build_runtime_command(record, host, port)
        startup_timeout_ms = int(((record.manifest or {}).get('health_policy') or {}).get('startup_timeout_ms') or 10000)

        process = subprocess.Popen(  # noqa: S603
            process_command,
            cwd=str(cwd or self._backend_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._processes[key] = process
        handle.process_id = process.pid
        handle.endpoint = runtime_endpoint

        try:
            health = self._wait_for_runtime(process, runtime_endpoint, startup_timeout_ms)
            handle.health = self._to_health_snapshot(record.plugin_id, health)
            if not health.healthy:
                handle.state = PluginRuntimeState.FAILED
                handle.last_error = health.message
            else:
                handle.state = PluginRuntimeState.RUNNING
        except Exception as exc:
            handle.state = PluginRuntimeState.FAILED
            handle.last_error = str(exc)
            self.stop_runtime(record.plugin_id, record.version)
            raise

        self._handles[key] = handle
        return handle

    def heartbeat(self, plugin_id: str, version: str, health: PluginHealthSnapshot) -> None:
        key = self._key(plugin_id, version)
        handle = self._handles.get(key)
        if handle is None:
            raise PluginSupervisorError(f'Runtime handle not found: {key}')
        handle.health = health
        if not health.healthy:
            handle.state = PluginRuntimeState.FAILED
            handle.last_error = health.message

    def drain_runtime(self, plugin_id: str, version: str) -> Optional[PluginRuntimeHandle]:
        handle = self._handles.get(self._key(plugin_id, version))
        if handle is None:
            return None
        handle.state = PluginRuntimeState.DRAINING
        handle.drained_at = utcnow_iso()
        return handle

    def stop_runtime(self, plugin_id: str, version: str) -> Optional[PluginRuntimeHandle]:
        key = self._key(plugin_id, version)
        handle = self._handles.get(key)
        process = self._processes.pop(key, None)
        if process is not None and process.poll() is None:
            if handle and handle.endpoint:
                try:
                    self._request_json(handle.endpoint, '/stop', payload={}, timeout=2.0)
                except Exception:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        if handle is None:
            return None
        handle.state = PluginRuntimeState.STOPPED
        return handle

    def mark_failed(self, plugin_id: str, version: str, message: str) -> Optional[PluginRuntimeHandle]:
        handle = self._handles.get(self._key(plugin_id, version))
        if handle is None:
            return None
        handle.state = PluginRuntimeState.FAILED
        handle.last_error = message
        return handle

    def get_handle(self, plugin_id: str, version: str) -> Optional[PluginRuntimeHandle]:
        return self._handles.get(self._key(plugin_id, version))

    def list_handles(self) -> list[PluginRuntimeHandle]:
        return list(self._handles.values())

    def invoke(self, target: PluginRoutingTarget, request: PluginInvokeRequest) -> PluginInvokeResponse:
        handle = self._handles.get(self._key(target.plugin_id, target.version))
        if handle is None or not handle.endpoint:
            return PluginInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=PluginRuntimeError.bad_response(
                    'Plugin runtime is not running',
                    details={'plugin_id': target.plugin_id, 'version': target.version},
                ),
            )

        payload = dict(request.payload)
        payload.setdefault('request_id', request.request_id)
        payload.setdefault('site_name', request.site_name)
        payload.setdefault('timeout_ms', request.timeout_ms)
        payload.setdefault('metadata', dict(request.metadata))

        outbound_request = PluginInvokeRequest(
            request_id=request.request_id,
            capability=request.capability,
            payload=payload,
            site_name=request.site_name,
            timeout_ms=request.timeout_ms,
            metadata=dict(request.metadata),
        )

        try:
            raw_response = self._request_json(
                handle.endpoint,
                '/invoke',
                payload={'request': outbound_request.to_dict()},
                timeout=max((request.timeout_ms or 5000) / 1000, 1.0),
            )
            response = PluginInvokeResponse.from_dict(raw_response)
            if handle.endpoint:
                try:
                    health = self._fetch_health(handle.endpoint, timeout=1.0)
                    handle.health = self._to_health_snapshot(target.plugin_id, health)
                    handle.state = PluginRuntimeState.RUNNING if health.healthy else PluginRuntimeState.FAILED
                except Exception:
                    pass
            return response
        except urllib.error.URLError as exc:
            self.mark_failed(target.plugin_id, target.version, str(exc))
            return PluginInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=PluginRuntimeError.network_error(
                    'Plugin runtime request failed',
                    details={'plugin_id': target.plugin_id, 'capability': target.capability, 'reason': str(exc)},
                ),
            )
        except Exception as exc:
            self.mark_failed(target.plugin_id, target.version, str(exc))
            return PluginInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=PluginRuntimeError.bad_response(
                    'Plugin runtime returned an invalid response object',
                    details={'plugin_id': target.plugin_id, 'capability': target.capability, 'reason': str(exc)},
                ),
            )
