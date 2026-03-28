from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import threading
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
        self._records: Dict[str, PluginInstallRecord] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._log_streams: Dict[str, tuple[object, object]] = {}
        self._runtime_timers: Dict[str, threading.Timer] = {}
        self._backend_root = Path(__file__).resolve().parent.parent

    def _key(self, plugin_id: str, version: str) -> str:
        return f'{plugin_id}:{version}'

    def _candidate_import_paths(self, record: PluginInstallRecord) -> list[str]:
        if record.runtime_python:
            return []

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
        python_executable = record.runtime_python or sys.executable
        module_name = 'squirrel_plugin_runner.runtime_bridge' if record.runtime_python else 'plugins.runtime_bridge'
        runtime_policy = self._runtime_policy(record)
        network_policy = self._network_policy(record)
        command = [
            python_executable,
            '-m',
            module_name,
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
        if record.data_path:
            command.extend(['--data-dir', record.data_path])
        for permission in record.granted_permissions:
            command.extend(['--granted-permission', permission])
        if network_policy:
            command.extend(['--network-policy', json.dumps(network_policy)])
        if runtime_policy.get('max_runtime_seconds') is not None:
            command.extend(['--max-runtime-seconds', str(runtime_policy['max_runtime_seconds'])])
        if runtime_policy.get('memory_limit_mb') is not None:
            command.extend(['--memory-limit-mb', str(runtime_policy['memory_limit_mb'])])
        if runtime_policy.get('cpu_time_limit_seconds') is not None:
            command.extend(['--cpu-time-limit-seconds', str(runtime_policy['cpu_time_limit_seconds'])])
        if runtime_policy.get('max_open_files') is not None:
            command.extend(['--max-open-files', str(runtime_policy['max_open_files'])])
        for import_path in self._candidate_import_paths(record):
            command.extend(['--import-path', import_path])
        return command

    def _runtime_policy(self, record: PluginInstallRecord) -> dict:
        metadata = ((record.manifest or {}).get('metadata') or {})
        policy = metadata.get('runtime_policy') or {}
        return dict(policy) if isinstance(policy, dict) else {}

    def _network_policy(self, record: PluginInstallRecord) -> dict:
        metadata = ((record.manifest or {}).get('metadata') or {})
        policy = metadata.get('network_policy')
        if isinstance(policy, dict):
            return dict(policy)
        if 'network:http' in set(record.granted_permissions):
            return {'mode': 'allow_all'}
        return {'mode': 'deny_all'}

    def _build_process_env(self, record: PluginInstallRecord) -> dict[str, str]:
        if not record.runtime_python:
            return dict(os.environ)

        whitelist = {
            'SYSTEMROOT',
            'SystemRoot',
            'WINDIR',
            'COMSPEC',
            'ComSpec',
            'TEMP',
            'TMP',
            'PATH',
            'PATHEXT',
            'OS',
            'NUMBER_OF_PROCESSORS',
            'PROCESSOR_ARCHITECTURE',
            'PROCESSOR_IDENTIFIER',
            'PROGRAMDATA',
            'PUBLIC',
            'USERPROFILE',
            'HOME',
            'HOMEDRIVE',
            'HOMEPATH',
            'LOCALAPPDATA',
            'APPDATA',
        }
        process_env = {
            key: value
            for key, value in os.environ.items()
            if key in whitelist
        }
        runtime_bin = str(Path(record.runtime_python).resolve().parent)
        existing_path = process_env.get('PATH', '')
        process_env['PATH'] = runtime_bin if not existing_path else os.pathsep.join([runtime_bin, existing_path])
        process_env.pop('PYTHONPATH', None)
        process_env.pop('VIRTUAL_ENV', None)
        process_env['SQUIRREL_PLUGIN_ID'] = record.plugin_id
        process_env['SQUIRREL_PLUGIN_VERSION'] = record.version
        process_env['SQUIRREL_PLUGIN_ISOLATED'] = '1'
        process_env['SQUIRREL_PLUGIN_SOURCE'] = str(record.metadata.get('source') or 'upload')
        process_env['SQUIRREL_PLUGIN_GRANTED_PERMISSIONS'] = ','.join(record.granted_permissions)
        process_env['SQUIRREL_PLUGIN_NETWORK_POLICY'] = json.dumps(self._network_policy(record))
        process_env['SQUIRREL_PLUGIN_RUNTIME_POLICY'] = json.dumps(self._runtime_policy(record))
        process_env['SQUIRREL_PLUGIN_DECLARED_PERMISSIONS'] = ','.join(
            str(item.get('name'))
            for item in ((record.manifest or {}).get('permissions') or [])
            if isinstance(item, dict) and item.get('name')
        )
        if record.data_path:
            process_env['SQUIRREL_PLUGIN_DATA_DIR'] = record.data_path
        return process_env

    def _resolve_runtime_cwd(self, record: PluginInstallRecord) -> Path:
        if record.runtime_python and record.data_path:
            return Path(record.data_path)
        if record.runtime_python:
            return Path(record.install_path)
        return self._backend_root

    def _resolve_artifact_paths(self, record: PluginInstallRecord) -> dict[str, Path]:
        base_dir = Path(record.data_path or record.install_path or self._backend_root)
        log_dir = base_dir / 'runtime-logs'
        audit_dir = base_dir / 'runtime-audit'
        return {
            'log_dir': log_dir,
            'stdout': log_dir / 'stdout.log',
            'stderr': log_dir / 'stderr.log',
            'audit': audit_dir / 'audit.jsonl',
        }

    def _append_audit_event(self, record: PluginInstallRecord, event: str, details: Optional[dict] = None) -> Path:
        artifact_paths = self._resolve_artifact_paths(record)
        audit_path = artifact_paths['audit']
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'timestamp': utcnow_iso(),
            'plugin_id': record.plugin_id,
            'version': record.version,
            'event': event,
            'details': dict(details or {}),
        }
        with audit_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + '\n')
        return audit_path

    def _schedule_runtime_expiry(self, key: str, record: PluginInstallRecord) -> None:
        runtime_policy = self._runtime_policy(record)
        max_runtime_seconds = runtime_policy.get('max_runtime_seconds')
        if max_runtime_seconds is None:
            return

        def _expire() -> None:
            self._append_audit_event(
                record,
                event='runtime_expired',
                details={'max_runtime_seconds': max_runtime_seconds},
            )
            self.mark_failed(record.plugin_id, record.version, 'runtime_expired')
            self.stop_runtime(record.plugin_id, record.version)

        timer = threading.Timer(float(max_runtime_seconds), _expire)
        timer.daemon = True
        timer.start()
        self._runtime_timers[key] = timer

    def _cancel_runtime_timer(self, key: str) -> None:
        timer = self._runtime_timers.pop(key, None)
        if timer is not None:
            timer.cancel()

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
        key = self._key(record.plugin_id, record.version)
        handle = PluginRuntimeHandle(
            plugin_id=record.plugin_id,
            version=record.version,
            state=PluginRuntimeState.STOPPED,
        )
        self._handles[key] = handle
        self._records[key] = record
        return handle

    def start_runtime(
        self,
        record: PluginInstallRecord,
        command: Optional[Sequence[str]] = None,
        cwd: Optional[Path] = None,
        endpoint: Optional[str] = None,
    ) -> PluginRuntimeHandle:
        key = self._key(record.plugin_id, record.version)
        self._records[key] = record
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
        process_cwd = cwd or self._resolve_runtime_cwd(record)
        process_env = self._build_process_env(record)
        artifact_paths = self._resolve_artifact_paths(record)
        artifact_paths['log_dir'].mkdir(parents=True, exist_ok=True)
        stdout_handle = artifact_paths['stdout'].open('ab')
        stderr_handle = artifact_paths['stderr'].open('ab')
        self._append_audit_event(
            record,
            event='runtime_starting',
            details={
                'cwd': str(process_cwd),
                'command': process_command,
            },
        )

        process = subprocess.Popen(  # noqa: S603
            process_command,
            cwd=str(process_cwd),
            env=process_env,
            stdout=stdout_handle,
            stderr=stderr_handle,
        )
        self._log_streams[key] = (stdout_handle, stderr_handle)
        self._processes[key] = process
        handle.process_id = process.pid
        handle.endpoint = runtime_endpoint

        try:
            health = self._wait_for_runtime(process, runtime_endpoint, startup_timeout_ms)
            handle.health = self._to_health_snapshot(record.plugin_id, health)
            if not health.healthy:
                handle.state = PluginRuntimeState.FAILED
                handle.last_error = health.message
                self._append_audit_event(record, event='runtime_unhealthy', details={'message': health.message})
            else:
                handle.state = PluginRuntimeState.RUNNING
                self._append_audit_event(
                    record,
                    event='runtime_started',
                    details={
                        'pid': process.pid,
                        'endpoint': runtime_endpoint,
                    },
                )
                self._schedule_runtime_expiry(key, record)
        except Exception as exc:
            handle.state = PluginRuntimeState.FAILED
            handle.last_error = str(exc)
            self._append_audit_event(record, event='runtime_failed', details={'reason': str(exc)})
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
        self._cancel_runtime_timer(key)
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
        log_streams = self._log_streams.pop(key, None)
        if log_streams is not None:
            for stream in log_streams:
                try:
                    stream.close()
                except Exception:
                    pass
        if handle is None:
            return None
        handle.state = PluginRuntimeState.STOPPED
        record = self._records.get(key)
        if record is not None:
            self._append_audit_event(record, event='runtime_stopped', details={})
        return handle

    def mark_failed(self, plugin_id: str, version: str, message: str) -> Optional[PluginRuntimeHandle]:
        key = self._key(plugin_id, version)
        handle = self._handles.get(key)
        if handle is None:
            return None
        handle.state = PluginRuntimeState.FAILED
        handle.last_error = message
        record = self._records.get(key)
        if record is not None:
            self._append_audit_event(record, event='runtime_marked_failed', details={'reason': message})
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
            record = self._records.get(self._key(target.plugin_id, target.version))
            if record is not None:
                self._append_audit_event(
                    record,
                    event='invoke_failed',
                    details={'capability': target.capability, 'reason': str(exc)},
                )
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
            record = self._records.get(self._key(target.plugin_id, target.version))
            if record is not None:
                self._append_audit_event(
                    record,
                    event='invoke_failed',
                    details={'capability': target.capability, 'reason': str(exc)},
                )
            return PluginInvokeResponse(
                request_id=request.request_id,
                ok=False,
                error=PluginRuntimeError.bad_response(
                    'Plugin runtime returned an invalid response object',
                    details={'plugin_id': target.plugin_id, 'capability': target.capability, 'reason': str(exc)},
                ),
            )
