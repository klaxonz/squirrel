from __future__ import annotations

import logging
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
from .store import SiteRuntimeStore
from .lifecycle import SiteRuntimeLifecycle

logger = logging.getLogger(__name__)


class SiteRuntimeSupervisor:
    """Coordinate site runtime records, runtime state, and routing.

    Composition roots (FastAPI lifespan for web, ``bootstrap_runtime`` for
    workers) construct exactly one of these and inject it down the call chain.
    Read methods (``list_site_runtimes`` / ``get_snapshot`` / ``gateway``)
    never mutate the store or gateway as a side effect — only explicit write
    entry points (``sync_workspace`` / ``bootstrap_enabled_site_runtimes`` /
    ``reload_enabled_site_runtimes`` / ``enable_site_runtime`` /
    ``disable_site_runtime``) do.
    """

    def __init__(
        self,
        store: SiteRuntimeStore | None = None,
        lifecycle: SiteRuntimeLifecycle | None = None,
        gateway: SiteRuntimeGateway | None = None,
        paths: SiteRuntimePaths | None = None,
    ) -> None:
        self._paths = paths or build_site_runtime_paths()
        self._store = store or SiteRuntimeStore(paths=self._paths)
        self._lifecycle = lifecycle or SiteRuntimeLifecycle()
        self._gateway = gateway or SiteRuntimeGateway(lifecycle=self._lifecycle)
        self._discovery = SiteRuntimeDiscovery(self._paths, self._store, self._gateway)

    @property
    def gateway(self) -> SiteRuntimeGateway:
        return self._gateway

    @property
    def lifecycle(self) -> SiteRuntimeLifecycle:
        return self._lifecycle

    # ------------------------------------------------------------------
    # Read paths — pure reads, no store/gateway mutation
    # ------------------------------------------------------------------

    def list_site_runtimes(self) -> list[SiteRuntimeRecord]:
        return self.scan_workspace().records

    def scan_workspace(self) -> SiteRuntimeDiscoveryResult:
        """Read-only workspace scan; does not persist."""
        return self._discovery.scan_workspace()

    def get_site_runtime(self, runtime_id: str) -> SiteRuntimeRecord | None:
        for record in self.list_site_runtimes():
            if record.runtime_id == runtime_id:
                return record
        return None

    def get_snapshot(self) -> SiteRuntimeSnapshot:
        discovery = self.scan_workspace()
        return SiteRuntimeSnapshot(
            records=discovery.records,
            runtimes=self._lifecycle.list_handles(),
            registrations=self._gateway.list_registrations(),
            discovery_errors=discovery.errors,
        )

    # ------------------------------------------------------------------
    # Write paths
    # ------------------------------------------------------------------

    def sync_workspace(self) -> SiteRuntimeDiscoveryResult:
        """Persist the latest workspace scan and resync gateway registrations."""
        result = self.scan_workspace()
        return self._discovery.apply_discovery_result(result)

    def enable_site_runtime(self, runtime_id: str) -> SiteRuntimeRecord | None:
        record = self.get_site_runtime(runtime_id)
        if record is None:
            return None
        record.enabled = True
        self._lifecycle.start_runtime(record)
        self._gateway.register_manifest(
            runtime_id=record.runtime_id,
            version=record.version,
            manifest=_manifest_from_record(record),
        )
        record.status = SiteRuntimeStatus.RUNNING
        return self._store.upsert(record)

    def disable_site_runtime(self, runtime_id: str) -> SiteRuntimeRecord | None:
        record = self.get_site_runtime(runtime_id)
        if record is None:
            return None
        self._gateway.unregister_plugin(runtime_id)
        self._lifecycle.stop_runtime(record.runtime_id, record.version)
        record.enabled = False
        record.status = SiteRuntimeStatus.DISABLED
        return self._store.upsert(record)

    def bootstrap_enabled_site_runtimes(self) -> list[SiteRuntimeRecord]:
        # Persist the current workspace scan before reading the enabled set.
        self.sync_workspace()
        enabled_records = [record for record in self.list_site_runtimes() if record.enabled]
        if not enabled_records:
            return []

        futures: list[tuple[SiteRuntimeRecord, Future[object]]] = []
        with ThreadPoolExecutor(
            max_workers=len(enabled_records), thread_name_prefix="site-runtime-bootstrap"
        ) as executor:
            for record in enabled_records:
                futures.append((record, executor.submit(self._lifecycle.start_runtime, record)))

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
                record.status = SiteRuntimeStatus.FAILED
                self._store.upsert(record)
                continue
            self._gateway.register_manifest(
                runtime_id=record.runtime_id,
                version=record.version,
                manifest=_manifest_from_record(record),
            )
            record.status = SiteRuntimeStatus.RUNNING
            self._store.upsert(record)
            started.append(record)
        if first_error is not None:
            raise first_error
        return started

    def shutdown_all(self) -> None:
        records = self.list_site_runtimes()
        for record in records:
            handle = self._lifecycle.stop_runtime(record.runtime_id, record.version)
            if handle is not None and record.enabled:
                record.status = SiteRuntimeStatus.STOPPED
                self._store.upsert(record)
        for record in records:
            self._gateway.unregister_plugin(record.runtime_id)

    def reload_enabled_site_runtimes(self) -> list[SiteRuntimeRecord]:
        self.shutdown_all()
        return self.bootstrap_enabled_site_runtimes()


def _manifest_from_record(record: SiteRuntimeRecord):
    from .models import SiteRuntimeManifest

    return SiteRuntimeManifest.from_dict(record.manifest)
