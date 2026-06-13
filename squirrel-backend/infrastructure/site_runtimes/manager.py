from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait

from .discovery import SiteRuntimeDiscovery
from .gateway import SiteRuntimeGateway
from .models import (
    SiteRuntimeDiscoveryResult,
    SiteRuntimeRecord,
    SiteRuntimeSnapshot,
    SiteRuntimeStatus,
)
from .paths import SiteRuntimePaths, build_site_runtime_paths
from .runtime_models import SiteRuntimeManifest
from .store import SiteRuntimeStore
from .supervisor import SiteRuntimeSupervisor


class SiteRuntimeManager:
    """Coordinate site runtime records, runtime state, and routing."""

    def __init__(
        self,
        store: SiteRuntimeStore | None = None,
        supervisor: SiteRuntimeSupervisor | None = None,
        gateway: SiteRuntimeGateway | None = None,
        paths: SiteRuntimePaths | None = None,
    ) -> None:
        self._paths = paths or build_site_runtime_paths()
        self._store = store or SiteRuntimeStore(paths=self._paths)
        self._supervisor = supervisor or SiteRuntimeSupervisor()
        self._gateway = gateway or SiteRuntimeGateway(invocation_client=self._supervisor)
        self._discovery = SiteRuntimeDiscovery(self._paths, self._store, self._gateway)
        self._gateway.set_registration_refresh(self._refresh_gateway_registrations)

    @property
    def gateway(self) -> SiteRuntimeGateway:
        return self._gateway

    def list_site_runtimes(self) -> list[SiteRuntimeRecord]:
        return self.discover_site_runtimes()

    def discover_site_runtimes(self) -> list[SiteRuntimeRecord]:
        return self.discover_site_runtime_result().records

    def discover_site_runtime_result(self) -> SiteRuntimeDiscoveryResult:
        return self._discovery.discover_workspace_site_runtimes()

    def get_site_runtime(self, runtime_id: str) -> SiteRuntimeRecord | None:
        for record in self.discover_site_runtimes():
            if record.runtime_id == runtime_id:
                return record
        return None

    def enable_site_runtime(self, runtime_id: str) -> SiteRuntimeRecord | None:
        record = self.get_site_runtime(runtime_id)
        if record is None:
            return None
        record.enabled = True
        record.status = SiteRuntimeStatus.RUNNING
        self._gateway.register_manifest(
            runtime_id=record.runtime_id,
            version=record.version,
            manifest=SiteRuntimeManifest.from_dict(record.manifest),
        )
        self._supervisor.start_runtime(record)
        return self._store.upsert(record)

    def disable_site_runtime(self, runtime_id: str) -> SiteRuntimeRecord | None:
        record = self.get_site_runtime(runtime_id)
        if record is None:
            return None
        self._gateway.unregister_plugin(runtime_id)
        self._supervisor.stop_runtime(record.runtime_id, record.version)
        record.enabled = False
        record.status = SiteRuntimeStatus.DISABLED
        return self._store.upsert(record)

    def get_snapshot(self) -> SiteRuntimeSnapshot:
        records = self.discover_site_runtimes()
        return SiteRuntimeSnapshot(
            records=records,
            runtimes=self._supervisor.list_handles(),
            registrations=self._gateway.list_registrations(),
            discovery_errors=self.discover_site_runtime_result().errors,
        )

    def bootstrap_enabled_site_runtimes(self) -> list[SiteRuntimeRecord]:
        enabled_records = [record for record in self.discover_site_runtimes() if record.enabled]
        if not enabled_records:
            return []

        for record in enabled_records:
            self._gateway.register_manifest(
                runtime_id=record.runtime_id,
                version=record.version,
                manifest=SiteRuntimeManifest.from_dict(record.manifest),
            )

        futures: list[tuple[SiteRuntimeRecord, Future[object]]] = []
        with ThreadPoolExecutor(max_workers=len(enabled_records), thread_name_prefix="site-runtime-bootstrap") as executor:
            for record in enabled_records:
                futures.append((record, executor.submit(self._supervisor.start_runtime, record)))

            _done, not_done = wait([future for _, future in futures], return_when="FIRST_EXCEPTION")
            if not_done:
                wait(not_done)

        started: list[SiteRuntimeRecord] = []
        first_error: Exception | None = None
        for record, future in futures:
            try:
                future.result()
            except Exception as exc:  # pragma: no cover - exercised via tests
                # process boundary -- one runtime startup failure should not crash the batch
                if first_error is None:
                    first_error = exc
                continue
            record.status = SiteRuntimeStatus.RUNNING
            self._store.upsert(record)
            started.append(record)
        if first_error is not None:
            raise first_error
        return started

    def shutdown_all(self) -> None:
        records = self.discover_site_runtimes()
        for record in records:
            handle = self._supervisor.stop_runtime(record.runtime_id, record.version)
            if handle is not None and record.enabled:
                record.status = SiteRuntimeStatus.STOPPED
                self._store.upsert(record)
        for record in records:
            self._gateway.unregister_plugin(record.runtime_id)

    def reload_enabled_site_runtimes(self) -> list[SiteRuntimeRecord]:
        self.shutdown_all()
        return self.bootstrap_enabled_site_runtimes()

    def _refresh_gateway_registrations(self) -> None:
        records = self.discover_site_runtimes()
        existing_runtime_ids = {registration.runtime_id for registration in self._gateway.list_registrations()}
        active_runtime_ids: set[str] = set()

        for record in records:
            active_runtime_ids.add(record.runtime_id)
            if not record.enabled:
                self._gateway.unregister_plugin(record.runtime_id)
                continue
            self._gateway.register_manifest(
                runtime_id=record.runtime_id,
                version=record.version,
                manifest=SiteRuntimeManifest.from_dict(record.manifest),
            )

        for runtime_id in existing_runtime_ids - active_runtime_ids:
            self._gateway.unregister_plugin(runtime_id)

_site_runtime_manager: SiteRuntimeManager | None = None


def get_site_runtime_manager() -> SiteRuntimeManager:
    global _site_runtime_manager
    if _site_runtime_manager is None:
        _site_runtime_manager = SiteRuntimeManager()
    return _site_runtime_manager


def bootstrap_site_runtimes() -> list[SiteRuntimeRecord]:
    return get_site_runtime_manager().bootstrap_enabled_site_runtimes()


def shutdown_site_runtimes() -> None:
    get_site_runtime_manager().shutdown_all()


def reload_site_runtimes() -> list[SiteRuntimeRecord]:
    return get_site_runtime_manager().reload_enabled_site_runtimes()



