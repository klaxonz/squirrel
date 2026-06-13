from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from shared_kernel.infrastructure.trace import get_trace_id

from .audit import SiteRuntimeAuditWriter
from .models import SiteRuntimeRecord


class SiteRuntimeProcessLauncher:
    def __init__(self, backend_root: Path, audit_writer: SiteRuntimeAuditWriter) -> None:
        self._backend_root = backend_root
        self._audit_writer = audit_writer

    def pick_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def build_runtime_command(self, record: SiteRuntimeRecord, host: str, port: int) -> list[str]:
        runtime_policy = self.runtime_policy(record)
        network_policy = self.network_policy(record)
        command = [
            sys.executable,
            "-m",
            "infrastructure.site_runtimes.runtime_bridge",
            "--entrypoint",
            record.entrypoint,
            "--runtime-id",
            record.runtime_id,
            "--version",
            record.version,
            "--host",
            host,
            "--port",
            str(port),
        ]
        if record.data_path:
            command.extend(["--data-dir", record.data_path])
        for permission in record.granted_permissions:
            command.extend(["--granted-permission", permission])
        if network_policy:
            command.extend(["--network-policy", json.dumps(network_policy)])
        if runtime_policy.get("max_runtime_seconds") is not None:
            command.extend(["--max-runtime-seconds", str(runtime_policy["max_runtime_seconds"])])
        for import_path in self.candidate_import_paths(record):
            command.extend(["--import-path", import_path])
        return command

    def build_process_env(self, record: SiteRuntimeRecord) -> dict[str, str]:
        allowed_keys = {
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "PYTHONPATH",
            "PYTHONIOENCODING",
        }
        process_env = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in allowed_keys
        }
        process_env["PYTHONUNBUFFERED"] = "1"
        process_env["SQUIRREL_SITE_RUNTIME_ID"] = record.runtime_id

        trace_id = get_trace_id()
        if trace_id:
            process_env["SQUIRREL_TRACE_ID"] = trace_id
        process_env["SQUIRREL_SITE_RUNTIME_VERSION"] = record.version
        process_env["SQUIRREL_SITE_RUNTIME_SOURCE"] = str(record.metadata.get("source") or "workspace")
        process_env["SQUIRREL_SITE_RUNTIME_GRANTED_PERMISSIONS"] = ",".join(record.granted_permissions)
        process_env["SQUIRREL_SITE_RUNTIME_NETWORK_POLICY"] = json.dumps(self.network_policy(record))
        process_env["SQUIRREL_SITE_RUNTIME_RUNTIME_POLICY"] = json.dumps(self.runtime_policy(record))
        process_env["SQUIRREL_SITE_RUNTIME_DECLARED_PERMISSIONS"] = ",".join(
            str(item.get("name"))
            for item in ((record.manifest or {}).get("permissions") or [])
            if isinstance(item, dict) and item.get("name")
        )
        if record.data_path:
            process_env["SQUIRREL_SITE_RUNTIME_DATA_DIR"] = record.data_path
        return process_env

    def resolve_runtime_cwd(self, record: SiteRuntimeRecord) -> Path:
        return self._backend_root

    def open_log_streams(self, record: SiteRuntimeRecord) -> tuple[object, object]:
        artifact_paths = self._audit_writer.resolve_artifact_paths(record)
        artifact_paths["log_dir"].mkdir(parents=True, exist_ok=True)
        return artifact_paths["stdout"].open("ab"), artifact_paths["stderr"].open("ab")

    def launch(
        self,
        record: SiteRuntimeRecord,
        command: Sequence[str],
        cwd: Path,
        env: dict[str, str],
        stdout_handle: object,
        stderr_handle: object,
    ) -> subprocess.Popen:
        return subprocess.Popen(  # noqa: S603
            list(command),
            cwd=str(cwd),
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
        )

    def candidate_import_paths(self, record: SiteRuntimeRecord) -> list[str]:
        candidates: list[Path] = []
        if record.runtime_path:
            candidates.append(Path(record.runtime_path))
        if record.install_path:
            install_path = Path(record.install_path)
            candidates.append(install_path / "src")
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
    def runtime_policy(record: SiteRuntimeRecord) -> dict:
        metadata = ((record.manifest or {}).get("metadata") or {})
        policy = metadata.get("runtime_policy") or {}
        return dict(policy) if isinstance(policy, dict) else {}

    @staticmethod
    def network_policy(record: SiteRuntimeRecord) -> dict:
        metadata = ((record.manifest or {}).get("metadata") or {})
        policy = metadata.get("network_policy")
        if isinstance(policy, dict):
            return dict(policy)
        if "network:http" in set(record.granted_permissions):
            return {"mode": "allow_all"}
        return {"mode": "deny_all"}
