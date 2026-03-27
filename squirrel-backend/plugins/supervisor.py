from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional, Sequence

from .models import (
    PluginHealthSnapshot,
    PluginInstallRecord,
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

    def _key(self, plugin_id: str, version: str) -> str:
        return f'{plugin_id}:{version}'

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
        if process is not None and process.poll() is None:
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
