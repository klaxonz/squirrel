import logging
from collections.abc import Callable, Generator
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from core.database import get_session as _default_get_session
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.subscription import Subscription
from models.video_extraction_projection import VideoExtractionProjection
from schemas.subscription.dto.sync_center_dto import SyncCenterItemDto, SyncCenterListDto, SyncCenterOverviewDto
from services.site_catalog_cache import format_datetime as _default_format_datetime
from services.site_catalog_cache import get_cached_site_catalog as _default_get_cached_site_catalog
from utils.site_catalog import SiteCatalog
from utils.site_icons import build_site_icon_url, resolve_site_icon_path

SessionFactory = Callable[[], Generator[Session, None, None]]

_UNSET = object()
EXTRACTION_PREVIEW_LIMIT = 40
logger = logging.getLogger(__name__)


class VideoExtractionCenterService:
    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        ensure_projection_seeded=_UNSET,
        format_datetime=None,
        get_cached_site_catalog=None,
    ):
        self._session_factory = session_factory or _default_get_session
        self._ensure_projection_seeded = ensure_projection_seeded
        self._format_datetime = format_datetime or _default_format_datetime
        self._get_cached_site_catalog = get_cached_site_catalog or _default_get_cached_site_catalog
        self._site_icon_url_cache: dict[str, str | None] = {}
        self._site_domain_index: dict[str, str] | None = None

    def _get_ensure_projection_seeded(self):
        if self._ensure_projection_seeded is _UNSET:
            from services import video_extraction_projection_service
            self._ensure_projection_seeded = video_extraction_projection_service.ensure_projection_seeded
        return self._ensure_projection_seeded

    @staticmethod
    def _summarize_error(message: str | None) -> str | None:
        if not message:
            return None

        normalized = str(message).strip()
        if not normalized:
            return None

        lowered = normalized.lower()
        if "extract" in lowered:
            return "提取失败"
        if "timeout" in lowered:
            return "处理超时"
        if "network" in lowered or "connection" in lowered:
            return "网络异常"

        first_line = normalized.splitlines()[0].strip()
        if len(first_line) <= 80:
            return first_line
        return first_line[:77] + "..."

    @staticmethod
    def _build_site_domain_index(catalog: dict[str, dict]) -> dict[str, str]:
        index: dict[str, str] = {}
        for slug, site_info in catalog.items():
            for domain in site_info.get('domains', []):
                if domain:
                    index[str(domain).strip().lower()] = slug
            for alias in site_info.get('aliases', []):
                if alias:
                    index[str(alias).strip().lower()] = slug
        return index

    def _resolve_site_icon_url(self, site: str | None) -> str | None:
        normalized_site = str(site or "").strip().lower()
        if not normalized_site:
            return None

        cached_icon_url = self._site_icon_url_cache.get(normalized_site)
        if normalized_site in self._site_icon_url_cache:
            return cached_icon_url

        catalog = self._get_cached_site_catalog()

        if normalized_site in catalog:
            site_slug = normalized_site
            catalog_entry = catalog[site_slug]
        else:
            site_slug = None
            catalog_entry = None

            if self._site_domain_index is None:
                self._site_domain_index = self._build_site_domain_index(catalog)

            slug = self._site_domain_index.get(normalized_site)
            if slug:
                site_slug = slug
                catalog_entry = catalog.get(slug)

        icon_url = str((catalog_entry or {}).get("icon_url") or "").strip() or None
        if icon_url:
            self._site_icon_url_cache[normalized_site] = icon_url
            return icon_url

        fallback_slug = site_slug or normalized_site
        if resolve_site_icon_path(fallback_slug):
            resolved_icon_url = build_site_icon_url(fallback_slug)
            self._site_icon_url_cache[normalized_site] = resolved_icon_url
            return resolved_icon_url

        self._site_icon_url_cache[normalized_site] = None
        return None

    @staticmethod
    def _build_run_id(group_kind: str, group_value: str) -> str:
        return f"extract:{group_kind}:{group_value}"

    @staticmethod
    def _derive_projection_group_key(task: CrawlTask) -> tuple[str, str]:
        payload = task.payload or {}
        run_id = payload.get("run_id")
        if run_id not in (None, ""):
            return "run", str(run_id)

        sync_state_id = payload.get("sync_state_id")
        if sync_state_id not in (None, ""):
            return "state", str(sync_state_id)

        return "job", str(task.job_id)

    @staticmethod
    def _resolve_task_sync_mode(task: CrawlTask) -> str:
        payload = task.payload or {}
        normalized_mode = str(payload.get("mode") or payload.get("sync_mode") or "").strip().lower()
        if normalized_mode in {"full", "incremental"}:
            return normalized_mode

        is_extract_all = payload.get("is_extract_all")
        if is_extract_all is True:
            return "full"

        if (
            is_extract_all is False
            or payload.get("run_id") not in (None, "")
            or payload.get("sync_state_id") not in (None, "")
        ):
            return "incremental"

        return "extract"

    @staticmethod
    def _preload_sync_mode_cache(
        session: Session,
        subscription_ids: set[int],
        cache: dict[tuple[int, str, str], str],
    ) -> None:
        if not subscription_ids:
            return

        tasks = (
            session.execute(
                select(CrawlTask)
                .where(
                    CrawlTask.task_type == "video_extract",
                    CrawlTask.subscription_id.in_(subscription_ids),
                )
                .order_by(CrawlTask.created_at.asc(), CrawlTask.id.asc()),
            )
            .scalars()
            .all()
        )

        for task in tasks:
            group_key = VideoExtractionCenterService._derive_projection_group_key(task)
            cache_key = (int(task.subscription_id), group_key[0], group_key[1])
            if cache_key not in cache:
                cache[cache_key] = VideoExtractionCenterService._resolve_task_sync_mode(task)

    @staticmethod
    def _resolve_projection_sync_mode(
        session: Session,
        projection: VideoExtractionProjection,
        cache: dict[tuple[int, str, str], str],
    ) -> str:
        cache_key = (int(projection.subscription_id), str(projection.group_kind), str(projection.group_value))
        cached_mode = cache.get(cache_key)
        if cached_mode:
            return cached_mode

        cache[cache_key] = "extract"
        return "extract"

    @staticmethod
    def _base_projection_query(
        user_id: int,
        *,
        site_candidates: set[str] | None = None,
        normalized_query: str = "",
    ) -> Any:
        query = (
            select(VideoExtractionProjection, Subscription)
            .join(Subscription, Subscription.id == VideoExtractionProjection.subscription_id)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            )
        )
        if site_candidates:
            query = query.where(VideoExtractionProjection.site.in_(site_candidates))
        if normalized_query:
            query = query.where(Subscription.name.ilike(f"%{normalized_query}%"))
        return query

    @staticmethod
    def _apply_status_filter(query: Any, status: str | None) -> Any:
        normalized_status = (status or "").strip().lower() or None
        if normalized_status == "running":
            return query.where(VideoExtractionProjection.display_status == "running")
        if normalized_status == "queued":
            return query.where(VideoExtractionProjection.display_status == "queued")
        if normalized_status == "failed":
            return query.where(VideoExtractionProjection.sync_status == "failed")
        if normalized_status == "recent":
            return query.where(VideoExtractionProjection.display_status.notin_(["running", "queued"]))
        return query

    @staticmethod
    def _apply_ordering(query: Any, status: str | None) -> Any:
        normalized_status = (status or "").strip().lower() or None
        if normalized_status == "running":
            return query.order_by(
                VideoExtractionProjection.locked_at.asc(), VideoExtractionProjection.subscription_id.asc()
            )
        if normalized_status == "queued":
            return query.order_by(
                VideoExtractionProjection.queued_at.asc(), VideoExtractionProjection.subscription_id.asc()
            )
        recent_dt = func.coalesce(VideoExtractionProjection.updated_at, VideoExtractionProjection.last_success_at)
        return query.order_by(recent_dt.desc(), VideoExtractionProjection.subscription_id.desc())

    def _build_item(
        self,
        session: Session,
        projection: VideoExtractionProjection,
        subscription: Subscription,
        sync_mode_cache: dict[tuple[int, str, str], str],
    ) -> SyncCenterItemDto:
        active_count = int(projection.pending_video_count or 0)
        processed_count = int(projection.completed_task_count or 0) + int(projection.failed_task_count or 0)
        sync_mode = self._resolve_projection_sync_mode(session, projection, sync_mode_cache)

        return SyncCenterItemDto(
            run_id=self._build_run_id(projection.group_kind, projection.group_value),
            subscription_id=subscription.id,
            subscription_name=subscription.name,
            subscription_avatar=subscription.avatar,
            site=projection.site,
            site_icon_url=self._resolve_site_icon_url(projection.site),
            sync_mode=sync_mode,
            sync_status=projection.sync_status,
            display_status=projection.display_status,
            current_phase=projection.current_phase,
            failure_count=int(projection.failed_task_count or 0),
            last_error=projection.last_error,
            last_error_summary=self._summarize_error(projection.last_error),
            last_sync_at="",
            last_success_at=self._format_datetime(projection.last_success_at if projection.sync_status == "success" else None),
            next_sync_at="",
            queued_at=self._format_datetime(projection.queued_at),
            locked_at=self._format_datetime(projection.locked_at),
            updated_at=self._format_datetime(projection.updated_at),
            pending_video_count=active_count,
            feed_completed=active_count == 0,
            has_more_pages=False,
            videos_found=int(projection.batch_task_count or 0),
            videos_enqueued=int(projection.queued_task_count or 0),
            videos_extracted=int(projection.completed_task_count or 0),
            videos_skipped=0,
            progress_percent=int((processed_count / projection.batch_task_count) * 100)
            if projection.batch_task_count
            else 0,
            progress_label=f"{processed_count} / {projection.batch_task_count}" if projection.batch_task_count else "",
            is_deferred=False,
            defer_reason=None,
            batch_task_count=int(projection.batch_task_count or 0),
            queued_task_count=int(projection.queued_task_count or 0),
            running_task_count=int(projection.running_task_count or 0),
            completed_task_count=int(projection.completed_task_count or 0),
            failed_task_count=int(projection.failed_task_count or 0),
        )

    def get_extraction_center_overview(self, user_id: int) -> SyncCenterOverviewDto:
        self._get_ensure_projection_seeded()()

        with self._session_factory() as session:
            query = (
                select(
                    func.coalesce(
                        func.sum(case((VideoExtractionProjection.display_status == "running", 1), else_=0)),
                        0,
                    ).label("running_count"),
                    func.coalesce(
                        func.sum(case((VideoExtractionProjection.display_status == "queued", 1), else_=0)),
                        0,
                    ).label("queued_count"),
                    func.coalesce(
                        func.sum(case((VideoExtractionProjection.sync_status == "failed", 1), else_=0)),
                        0,
                    ).label("failed_count"),
                    func.coalesce(func.sum(VideoExtractionProjection.pending_video_count), 0).label("pending_videos"),
                    func.coalesce(func.sum(VideoExtractionProjection.queued_task_count), 0).label("queue_depth"),
                )
                .select_from(VideoExtractionProjection)
                .join(Subscription, Subscription.id == VideoExtractionProjection.subscription_id)
                .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                    Subscription.is_deleted.is_(False),
                )
            )
            row = session.execute(query).one()

        return SyncCenterOverviewDto(
            running_count=int(row.running_count or 0),
            queued_count=int(row.queued_count or 0),
            failed_count=int(row.failed_count or 0),
            due_soon_count=0,
            deferred_count=0,
            pending_videos=int(row.pending_videos or 0),
            queue_depth=int(row.queue_depth or 0),
            queue_messages=0,
        )

    def get_extraction_dashboard_snapshot(self, user_id: int, *, preview_limit: int = EXTRACTION_PREVIEW_LIMIT) -> dict:
        overview = self.get_extraction_center_overview(user_id)
        running_count = int(overview.running_count or 0)
        queued_count = int(overview.queued_count or 0)
        running_preview = (
            self.list_extraction_center_items(user_id, "running", None, None, 1, running_count).data if running_count > 0 else []
        )
        queued_preview = (
            self.list_extraction_center_items(user_id, "queued", None, None, 1, queued_count).data if queued_count > 0 else []
        )
        recent_preview = self.list_extraction_center_items(user_id, "recent", None, None, 1, preview_limit).data
        return {
            "overview": overview,
            "runningPreview": running_preview,
            "queuedPreview": queued_preview,
            "recentPreview": recent_preview,
        }

    def list_extraction_center_items(
        self,
        user_id: int,
        status: str | None,
        site: str | None,
        query: str | None,
        page: int,
        page_size: int,
    ) -> SyncCenterListDto:
        self._get_ensure_projection_seeded()()

        normalized_status = (status or "").strip().lower() or None
        normalized_site = (site or "").strip().lower() or None
        site_candidates = set(SiteCatalog.expand_site_filter_values(normalized_site)) if normalized_site else set()
        normalized_query = (query or "").strip().lower()
        start = max(0, (page - 1) * page_size)

        filtered_query = self._apply_status_filter(
            self._base_projection_query(
                user_id,
                site_candidates=site_candidates,
                normalized_query=normalized_query,
            ),
            normalized_status,
        )
        ordered_query = self._apply_ordering(filtered_query, normalized_status)

        with self._session_factory() as session:
            total = int(
                session.execute(
                    select(func.count()).select_from(filtered_query.order_by(None).subquery()),
                ).scalar()
                or 0,
            )
            rows = session.execute(
                ordered_query.offset(start).limit(page_size),
            ).all()
            sync_mode_cache: dict[tuple[int, str, str], str] = {}
            sub_ids = {int(projection.subscription_id) for projection, _ in rows}
            self._preload_sync_mode_cache(session, sub_ids, sync_mode_cache)
            items = [self._build_item(session, projection, subscription, sync_mode_cache) for projection, subscription in rows]

        if normalized_status == "queued":
            for index, item in enumerate(items, start=start + 1):
                item.queue_position = index

        return SyncCenterListDto(
            total=total,
            page=page,
            page_size=page_size,
            data=items,
        )


_default = VideoExtractionCenterService()
get_extraction_center_overview = _default.get_extraction_center_overview
get_extraction_dashboard_snapshot = _default.get_extraction_dashboard_snapshot
list_extraction_center_items = _default.list_extraction_center_items
