import logging
from collections.abc import Callable, Generator

from sqlalchemy.orm import Session

from core.database import get_session as _default_get_session
from schemas.subscription.dto.sync_dashboard_dto import (
    SyncDashboardItemDto,
    SyncDashboardListDto,
    SyncDashboardOverviewDto,
)
from services.site_catalog.cache import format_datetime as _default_format_datetime
from services.sync_dashboard.site_icons import SiteIconResolver
from services.video.extraction_center.queries import list_projection_rows, overview_query
from services.video.extraction_center.serialization import build_extraction_item
from services.video.extraction_center.sync_mode import (
    SyncModeCache,
    preload_sync_mode_cache,
    resolve_projection_sync_mode,
)

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
        site_icon_resolver: SiteIconResolver | None = None,
    ):
        self._session_factory = session_factory or _default_get_session
        self._ensure_projection_seeded = ensure_projection_seeded
        self._format_datetime = format_datetime or _default_format_datetime
        self._site_icon_resolver = site_icon_resolver or SiteIconResolver()

    def _get_ensure_projection_seeded(self):
        if self._ensure_projection_seeded is _UNSET:
            import services.video.extraction_projection as video_extraction_projection
            self._ensure_projection_seeded = video_extraction_projection.ensure_projection_seeded
        return self._ensure_projection_seeded

    def _build_item(
        self,
        session: Session,
        projection,
        subscription,
        sync_mode_cache: SyncModeCache,
    ) -> SyncDashboardItemDto:
        return build_extraction_item(
            projection,
            subscription,
            sync_mode=resolve_projection_sync_mode(projection, sync_mode_cache),
            format_datetime=self._format_datetime,
            site_icon_resolver=self._site_icon_resolver,
        )

    def get_extraction_center_overview(self, user_id: int) -> SyncDashboardOverviewDto:
        self._get_ensure_projection_seeded()()

        with self._session_factory() as session:
            row = session.execute(overview_query(user_id)).one()

        return SyncDashboardOverviewDto(
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
    ) -> SyncDashboardListDto:
        self._get_ensure_projection_seeded()()

        normalized_status = (status or "").strip().lower() or None
        start = max(0, (page - 1) * page_size)

        with self._session_factory() as session:
            rows, total = list_projection_rows(
                session,
                user_id=user_id,
                status=normalized_status,
                site=site,
                query=query,
                page=page,
                page_size=page_size,
            )
            sync_mode_cache: SyncModeCache = {}
            sub_ids = {int(projection.subscription_id) for projection, _ in rows}
            preload_sync_mode_cache(session, sub_ids, sync_mode_cache)
            items = [self._build_item(session, projection, subscription, sync_mode_cache) for projection, subscription in rows]

        if normalized_status == "queued":
            for index, item in enumerate(items, start=start + 1):
                item.queue_position = index

        return SyncDashboardListDto(
            total=total,
            page=page,
            page_size=page_size,
            data=items,
        )


video_extraction_center_service = VideoExtractionCenterService()
get_extraction_center_overview = video_extraction_center_service.get_extraction_center_overview
get_extraction_dashboard_snapshot = video_extraction_center_service.get_extraction_dashboard_snapshot
list_extraction_center_items = video_extraction_center_service.list_extraction_center_items
