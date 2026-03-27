from __future__ import annotations

import importlib
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence

from crawl import PluginHealthStatus, PluginInvokeRequest, PluginInvokeResponse, PluginRuntime, PluginRuntimeError

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
    """Manage plugin runtime handles and optional subprocesses."""

    def __init__(self) -> None:
        self._handles: Dict[str, PluginRuntimeHandle] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._runtimes: Dict[str, PluginRuntime] = {}
        self._import_paths: set[str] = set()

    def _key(self, plugin_id: str, version: str) -> str:
        return f'{plugin_id}:{version}'

    def _ensure_import_path(self, record: PluginInstallRecord) -> None:
        candidates = []
        if record.runtime_path:
            candidates.append(Path(record.runtime_path))
        if record.install_path:
            install_path = Path(record.install_path)
            candidates.append(install_path / 'src')
            candidates.append(install_path)

        for candidate in candidates:
            if not candidate.exists():
                continue
            path_str = str(candidate.resolve())
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
            self._import_paths.add(path_str)

    def _load_runtime(self, record: PluginInstallRecord) -> PluginRuntime:
        self._ensure_import_path(record)
        module_name, _, factory_name = record.entrypoint.partition(':')
        if not module_name or not factory_name:
            raise PluginSupervisorError(f'Invalid runtime entrypoint: {record.entrypoint}')

        importlib.invalidate_caches()
        module = importlib.import_module(module_name)
        factory = getattr(module, factory_name, None)
        if factory is None:
            raise PluginSupervisorError(f'Runtime factory not found: {record.entrypoint}')

        runtime = factory()
        if not isinstance(runtime, PluginRuntime):
            raise PluginSupervisorError(f'Runtime factory did not return PluginRuntime: {record.entrypoint}')
        return runtime

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

        if command:
            process = subprocess.Popen(  # noqa: S603
                list(command),
                cwd=str(cwd) if cwd else None,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._processes[key] = process
            handle.process_id = process.pid
        else:
            runtime = self._load_runtime(record)
            runtime.start({
                'plugin_id': record.plugin_id,
                'version': record.version,
            })
            self._runtimes[key] = runtime
            health = runtime.health()
            handle.endpoint = endpoint or f'local://{record.plugin_id}/{record.version}'
            handle.health = self._to_health_snapshot(record.plugin_id, health)
            if not health.healthy:
                handle.state = PluginRuntimeState.FAILED
                handle.last_error = health.message

        if handle.state != PluginRuntimeState.FAILED:
            handle.state = PluginRuntimeState.RUNNING
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
        runtime = self._runtimes.pop(key, None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        if runtime is not None:
            runtime.stop()
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
        runtime = self._runtimes.get(self._key(target.plugin_id, target.version))
        if runtime is None:
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

        response = runtime.invoke(target.capability, payload)
        if isinstance(response, PluginInvokeResponse):
            return response
        if isinstance(response, dict):
            return PluginInvokeResponse.from_dict(response)
        return PluginInvokeResponse(
            request_id=request.request_id,
            ok=False,
            error=PluginRuntimeError.bad_response(
                'Plugin runtime returned an unsupported response type',
                details={'plugin_id': target.plugin_id, 'capability': target.capability},
            ),
        )
