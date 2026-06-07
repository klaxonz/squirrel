from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Generator
from datetime import datetime
from threading import Lock
from time import monotonic

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.database import get_session as _default_get_session
from core.database import register_after_commit
from models.crawl_task import CrawlTask
from models.video_extraction_projection import VideoExtractionProjection

SessionFactory = Callable[[], Generator[Session, None, None]]

_UNSET = object()

RUNNING_TASK_STATUSES = {"leased", "running"}
QUEUED_TASK_STATUSES = {"pending", "retry_wait"}
FAILED_TASK_STATUSES = {"dead", "cancelled"}
COMPLETED_TASK_STATUSES = {"succeeded"}
VIDEO_EXTRACT_TASK_TYPE = "video_extract"
ACTIVE_PROJECTION_STATUSES = {"running", "queued"}
RECONCILE_INTERVAL_SECONDS = 30


class VideoExtractionProjectionService:
    _seed_lock = Lock()

    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        publish_sync_center_invalidation=_UNSET,
        sync_center_extract_channel=_UNSET,
    ):
        self._session_factory = session_factory or _default_get_session
        self._publish_sync_center_invalidation = publish_sync_center_invalidation
        self._sync_center_extract_channel = sync_center_extract_channel
        self._last_reconcile_monotonic: float | None = None
        self._group_key_layout_checked = False

    def _get_publish_sync_center_invalidation(self):
        if self._publish_sync_center_invalidation is _UNSET:
            from services import sync_center_stream_service
            self._publish_sync_center_invalidation = sync_center_stream_service.publish_sync_center_invalidation
        return self._publish_sync_center_invalidation

    def _get_sync_center_extract_channel(self):
        if self._sync_center_extract_channel is _UNSET:
            from services import sync_center_stream_service
            self._sync_center_extract_channel = sync_center_stream_service.SYNC_CENTER_EXTRACT_CHANNEL
        return self._sync_center_extract_channel

    @staticmethod
    def _sync_state_value_expr():
        return func.nullif(CrawlTask.payload["sync_state_id"].as_string(), "")

    @staticmethod
    def _derive_group_key(task: CrawlTask) -> tuple[str, str]:
        payload = task.payload or {}
        run_id = payload.get("run_id")
        if run_id not in (None, ""):
            return "run", str(run_id)
        sync_state_id = payload.get("sync_state_id")
        if sync_state_id not in (None, ""):
            return "state", str(sync_state_id)
        return "job", str(task.job_id)

    @staticmethod
    def _compute_projection_snapshot(tasks: list[CrawlTask]) -> dict[str, object]:
        total_count = len(tasks)
        queued_count = sum(1 for task in tasks if task.status in QUEUED_TASK_STATUSES)
        running_count = sum(1 for task in tasks if task.status in RUNNING_TASK_STATUSES)
        completed_count = sum(1 for task in tasks if task.status in COMPLETED_TASK_STATUSES)
        failed_count = sum(1 for task in tasks if task.status in FAILED_TASK_STATUSES)
        active_count = queued_count + running_count

        if running_count > 0:
            sync_status = "running"
            display_status = "running"
            current_phase = "extracting"
        elif active_count > 0:
            sync_status = "queued"
            display_status = "queued"
            current_phase = "queued"
        elif failed_count > 0:
            sync_status = "failed"
            display_status = "failed"
            current_phase = "completed"
        else:
            sync_status = "success"
            display_status = "healthy"
            current_phase = "completed"

        latest_failed_task = max(
            (task for task in tasks if task.status in FAILED_TASK_STATUSES),
            key=lambda item: (item.updated_at or datetime.min, item.id),
            default=None,
        )

        queued_at = min((task.created_at for task in tasks if task.created_at), default=None)
        locked_at = min((task.started_at for task in tasks if task.started_at), default=None)
        updated_at = max((task.updated_at for task in tasks if task.updated_at), default=None)
        last_success_at = max(
            (task.finished_at for task in tasks if task.status in COMPLETED_TASK_STATUSES and task.finished_at),
            default=None,
        )
        first_task = tasks[0] if tasks else None

        return {
            "site": first_task.site if first_task else None,
            "sync_status": sync_status,
            "display_status": display_status,
            "current_phase": current_phase,
            "last_error": latest_failed_task.last_error if latest_failed_task else None,
            "queued_at": queued_at,
            "locked_at": locked_at,
            "last_success_at": last_success_at if sync_status == "success" else None,
            "pending_video_count": active_count,
            "batch_task_count": total_count,
            "queued_task_count": queued_count,
            "running_task_count": running_count,
            "completed_task_count": completed_count,
            "failed_task_count": failed_count,
            "updated_at": updated_at or datetime.now(),
        }

    @staticmethod
    def _upsert_projection(
        session: Session,
        *,
        subscription_id: int,
        group_kind: str,
        group_value: str,
        snapshot: dict[str, object],
    ) -> None:
        projection = session.execute(
            select(VideoExtractionProjection).where(
                VideoExtractionProjection.subscription_id == subscription_id,
                VideoExtractionProjection.group_kind == group_kind,
                VideoExtractionProjection.group_value == group_value,
            ),
        ).scalar_one_or_none()

        if projection is None:
            projection = VideoExtractionProjection(
                subscription_id=subscription_id,
                group_kind=group_kind,
                group_value=group_value,
            )
            session.add(projection)

        for key, value in snapshot.items():
            setattr(projection, key, value)

    def refresh_projection_for_task(self, task: CrawlTask, *, session: Session | None = None) -> None:
        if task.task_type != VIDEO_EXTRACT_TASK_TYPE or task.subscription_id is None:
            return

        group_kind, group_value = self._derive_group_key(task)
        if session is not None:
            self._refresh_projection_group(session, subscription_id=int(task.subscription_id), group_kind=group_kind, group_value=group_value)
            register_after_commit(
                session,
                lambda: self._get_publish_sync_center_invalidation()(
                    self._get_sync_center_extract_channel(),
                    {"run_id": (task.payload or {}).get("run_id")},
                ),
            )
            return

        with self._session_factory() as managed_session:
            self._refresh_projection_group(
                managed_session,
                subscription_id=int(task.subscription_id),
                group_kind=group_kind,
                group_value=group_value,
            )
            register_after_commit(
                managed_session,
                lambda: self._get_publish_sync_center_invalidation()(
                    self._get_sync_center_extract_channel(),
                    {"run_id": (task.payload or {}).get("run_id")},
                ),
            )

    @staticmethod
    def _refresh_projection_group(
        session: Session,
        *,
        subscription_id: int,
        group_kind: str,
        group_value: str,
    ) -> None:
        subscription_tasks = session.execute(
            select(CrawlTask)
            .where(
                CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE,
                CrawlTask.subscription_id == subscription_id,
            )
            .order_by(CrawlTask.created_at.asc(), CrawlTask.id.asc()),
        ).scalars().all()
        tasks = [
            task for task in subscription_tasks
            if VideoExtractionProjectionService._derive_group_key(task) == (group_kind, str(group_value))
        ]

        projection = session.execute(
            select(VideoExtractionProjection).where(
                VideoExtractionProjection.subscription_id == subscription_id,
                VideoExtractionProjection.group_kind == group_kind,
                VideoExtractionProjection.group_value == group_value,
            ),
        ).scalar_one_or_none()

        if not tasks:
            if projection is not None:
                session.delete(projection)
            return

        snapshot = VideoExtractionProjectionService._compute_projection_snapshot(tasks)
        VideoExtractionProjectionService._upsert_projection(
            session,
            subscription_id=subscription_id,
            group_kind=group_kind,
            group_value=group_value,
            snapshot=snapshot,
        )

    def rebuild_all_projections(self, *, session: Session | None = None) -> int:
        if session is not None:
            return self._rebuild_all(session)

        with self._session_factory() as managed_session:
            return self._rebuild_all(managed_session)

    @staticmethod
    def _rebuild_all(session: Session) -> int:
        tasks = session.execute(
            select(CrawlTask)
            .where(CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE)
            .order_by(CrawlTask.subscription_id.asc(), CrawlTask.job_id.asc(), CrawlTask.created_at.asc(), CrawlTask.id.asc()),
        ).scalars().all()

        session.execute(VideoExtractionProjection.__table__.delete())
        grouped: dict[tuple[int, str, str], list[CrawlTask]] = defaultdict(list)
        for task in tasks:
            if task.subscription_id is None:
                continue
            group_kind, group_value = VideoExtractionProjectionService._derive_group_key(task)
            grouped[(int(task.subscription_id), group_kind, group_value)].append(task)

        for (subscription_id, group_kind, group_value), group_tasks in grouped.items():
            VideoExtractionProjectionService._upsert_projection(
                session,
                subscription_id=subscription_id,
                group_kind=group_kind,
                group_value=group_value,
                snapshot=VideoExtractionProjectionService._compute_projection_snapshot(group_tasks),
            )

        session.flush()
        return len(grouped)

    @staticmethod
    def _load_active_task_group_keys(session: Session) -> set[tuple[int, str, str]]:
        tasks = session.execute(
            select(CrawlTask)
            .where(
                CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE,
                CrawlTask.status.in_(RUNNING_TASK_STATUSES | QUEUED_TASK_STATUSES),
                CrawlTask.subscription_id.is_not(None),
            ),
        ).scalars().all()

        keys: set[tuple[int, str, str]] = set()
        for task in tasks:
            if task.subscription_id is None:
                continue
            group_kind, group_value = VideoExtractionProjectionService._derive_group_key(task)
            keys.add((int(task.subscription_id), group_kind, group_value))
        return keys

    @staticmethod
    def _load_active_projection_group_keys(session: Session) -> set[tuple[int, str, str]]:
        rows = session.execute(
            select(
                VideoExtractionProjection.subscription_id,
                VideoExtractionProjection.group_kind,
                VideoExtractionProjection.group_value,
            ).where(VideoExtractionProjection.display_status.in_(ACTIVE_PROJECTION_STATUSES)),
        ).all()
        return {
            (int(subscription_id), str(group_kind), str(group_value))
            for subscription_id, group_kind, group_value in rows
        }

    @staticmethod
    def _projection_requires_group_key_rebuild(session: Session) -> bool:
        state_rows = session.execute(
            select(
                VideoExtractionProjection.subscription_id,
                VideoExtractionProjection.group_value,
            ).where(VideoExtractionProjection.group_kind == "state"),
        ).all()
        if not state_rows:
            return False

        state_keys = {
            (int(subscription_id), str(group_value))
            for subscription_id, group_value in state_rows
        }
        tasks = session.execute(
            select(CrawlTask)
            .where(
                CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE,
                CrawlTask.subscription_id.is_not(None),
            )
            .limit(1000),
        ).scalars().all()

        for task in tasks:
            if task.subscription_id is None:
                continue
            payload = task.payload or {}
            run_id = payload.get("run_id")
            sync_state_id = payload.get("sync_state_id")
            if run_id in (None, "") or sync_state_id in (None, ""):
                continue
            if (int(task.subscription_id), str(sync_state_id)) in state_keys:
                return True

        return False

    def reconcile_active_projection_drift(self, *, force: bool = False, session: Session | None = None) -> int:
        now_tick = monotonic()
        if not force and self._last_reconcile_monotonic is not None:
            if now_tick - self._last_reconcile_monotonic < RECONCILE_INTERVAL_SECONDS:
                return 0

        if session is not None:
            refreshed = self._reconcile_active_projection_drift(session)
            self._last_reconcile_monotonic = now_tick
            return refreshed

        with self.__class__._seed_lock:
            now_tick = monotonic()
            if not force and self._last_reconcile_monotonic is not None:
                if now_tick - self._last_reconcile_monotonic < RECONCILE_INTERVAL_SECONDS:
                    return 0

            with self._session_factory() as managed_session:
                refreshed = self._reconcile_active_projection_drift(managed_session)
            self._last_reconcile_monotonic = now_tick
            return refreshed

    @staticmethod
    def _reconcile_active_projection_drift(session: Session) -> int:
        active_task_keys = VideoExtractionProjectionService._load_active_task_group_keys(session)
        active_projection_keys = VideoExtractionProjectionService._load_active_projection_group_keys(session)
        stale_keys = active_task_keys | active_projection_keys

        refreshed = 0
        for subscription_id, group_kind, group_value in stale_keys:
            VideoExtractionProjectionService._refresh_projection_group(
                session,
                subscription_id=subscription_id,
                group_kind=group_kind,
                group_value=group_value,
            )
            refreshed += 1

        session.flush()
        return refreshed

    def ensure_projection_seeded(self) -> int:
        with self.__class__._seed_lock, self._session_factory() as session:
            projection_count = int(session.execute(select(func.count(VideoExtractionProjection.id))).scalar() or 0)
            if projection_count > 0:
                if not self._group_key_layout_checked:
                    if self._projection_requires_group_key_rebuild(session):
                        rebuilt = self._rebuild_all(session)
                        self._group_key_layout_checked = True
                        self._last_reconcile_monotonic = monotonic()
                        return rebuilt
                    self._group_key_layout_checked = True
                now_tick = monotonic()
                if self._last_reconcile_monotonic is not None:
                    if now_tick - self._last_reconcile_monotonic < RECONCILE_INTERVAL_SECONDS:
                        return 0
                refreshed = self._reconcile_active_projection_drift(session)
                self._last_reconcile_monotonic = now_tick
                return refreshed

            task_count = int(
                session.execute(
                    select(func.count(CrawlTask.id)).where(CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE),
                ).scalar()
                or 0,
            )
            if task_count == 0:
                return 0

            rebuilt = self._rebuild_all(session)
            self._group_key_layout_checked = True
            return rebuilt


_default = VideoExtractionProjectionService()
refresh_projection_for_task = _default.refresh_projection_for_task
rebuild_all_projections = _default.rebuild_all_projections
reconcile_active_projection_drift = _default.reconcile_active_projection_drift
ensure_projection_seeded = _default.ensure_projection_seeded
