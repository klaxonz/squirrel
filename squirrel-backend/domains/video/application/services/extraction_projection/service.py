from __future__ import annotations

from collections.abc import Callable, Generator
from threading import Lock
from time import monotonic

from sqlalchemy.orm import Session

import domains.video.application.services.extraction_projection.store as store
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.video.application.services.extraction_projection.groups import VIDEO_EXTRACT_TASK_TYPE, derive_group_key
from infrastructure.database.session import get_session as _default_get_session
from infrastructure.database.session import register_after_commit as _default_register_after_commit

SessionFactory = Callable[[], Generator[Session, None, None]]

_UNSET = object()
RECONCILE_INTERVAL_SECONDS = 30


class VideoExtractionProjectionService:
    _seed_lock = Lock()

    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        publish_sync_dashboard_invalidation=_UNSET,
        sync_dashboard_extract_channel=_UNSET,
    ):
        self._session_factory = session_factory or _default_get_session
        self._publish_sync_dashboard_invalidation = publish_sync_dashboard_invalidation
        self._sync_dashboard_extract_channel = sync_dashboard_extract_channel
        self._last_reconcile_monotonic: float | None = None
        self._group_key_layout_checked = False

    def _get_publish_sync_dashboard_invalidation(self):
        if self._publish_sync_dashboard_invalidation is _UNSET:
            from domains.subscription.application.services.sync import stream_service as sync_dashboard_stream_service
            self._publish_sync_dashboard_invalidation = (
                sync_dashboard_stream_service.sync_dashboard_stream_service.publish_sync_dashboard_invalidation
            )
        return self._publish_sync_dashboard_invalidation

    def _get_sync_dashboard_extract_channel(self):
        if self._sync_dashboard_extract_channel is _UNSET:
            from domains.subscription.application.services.sync import stream_service as sync_dashboard_stream_service
            self._sync_dashboard_extract_channel = sync_dashboard_stream_service.SYNC_DASHBOARD_EXTRACT_CHANNEL
        return self._sync_dashboard_extract_channel

    def refresh_projection_for_task(self, task: CrawlTask, *, session: Session | None = None) -> None:
        if task.task_type != VIDEO_EXTRACT_TASK_TYPE or task.subscription_id is None:
            return

        group_kind, group_value = derive_group_key(task)
        if session is not None:
            store.refresh_projection_group(
                session,
                subscription_id=int(task.subscription_id),
                group_kind=group_kind,
                group_value=group_value,
            )
            self._register_extract_invalidation(session, task)
            return

        with self._session_factory() as managed_session:
            store.refresh_projection_group(
                managed_session,
                subscription_id=int(task.subscription_id),
                group_kind=group_kind,
                group_value=group_value,
            )
            self._register_extract_invalidation(managed_session, task)

    def rebuild_all_projections(self, *, session: Session | None = None) -> int:
        if session is not None:
            return store.rebuild_all(session)

        with self._session_factory() as managed_session:
            return store.rebuild_all(managed_session)

    def reconcile_active_projection_drift(self, *, force: bool = False, session: Session | None = None) -> int:
        now_tick = monotonic()
        if not force and self._last_reconcile_monotonic is not None:
            if now_tick - self._last_reconcile_monotonic < RECONCILE_INTERVAL_SECONDS:
                return 0

        if session is not None:
            refreshed = store.reconcile_active_projection_drift(session)
            self._last_reconcile_monotonic = now_tick
            return refreshed

        with self.__class__._seed_lock:
            now_tick = monotonic()
            if not force and self._last_reconcile_monotonic is not None:
                if now_tick - self._last_reconcile_monotonic < RECONCILE_INTERVAL_SECONDS:
                    return 0

            with self._session_factory() as managed_session:
                refreshed = store.reconcile_active_projection_drift(managed_session)
            self._last_reconcile_monotonic = now_tick
            return refreshed

    def ensure_projection_seeded(self) -> int:
        with self.__class__._seed_lock, self._session_factory() as session:
            if store.count_projections(session) > 0:
                if not self._group_key_layout_checked:
                    if store.projection_requires_group_key_rebuild(session):
                        rebuilt = store.rebuild_all(session)
                        self._group_key_layout_checked = True
                        self._last_reconcile_monotonic = monotonic()
                        return rebuilt
                    self._group_key_layout_checked = True
                return self._reconcile_seeded_projection(session)

            if store.count_video_extract_tasks(session) == 0:
                return 0

            rebuilt = store.rebuild_all(session)
            self._group_key_layout_checked = True
            return rebuilt

    def _reconcile_seeded_projection(self, session: Session) -> int:
        now_tick = monotonic()
        if self._last_reconcile_monotonic is not None:
            if now_tick - self._last_reconcile_monotonic < RECONCILE_INTERVAL_SECONDS:
                return 0
        refreshed = store.reconcile_active_projection_drift(session)
        self._last_reconcile_monotonic = now_tick
        return refreshed

    def _register_extract_invalidation(self, session: Session, task: CrawlTask) -> None:
        _default_register_after_commit(
            session,
            lambda: self._get_publish_sync_dashboard_invalidation()(
                self._get_sync_dashboard_extract_channel(),
                {'run_id': (task.payload or {}).get('run_id')},
            ),
        )


video_extraction_projection_service = VideoExtractionProjectionService()
refresh_projection_for_task = video_extraction_projection_service.refresh_projection_for_task
rebuild_all_projections = video_extraction_projection_service.rebuild_all_projections
reconcile_active_projection_drift = video_extraction_projection_service.reconcile_active_projection_drift
ensure_projection_seeded = video_extraction_projection_service.ensure_projection_seeded
