from datetime import datetime
import logging
from threading import Lock
from time import monotonic
from typing import Any, Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from core.database import get_session
from core.site_config_manager import get_effective_site_catalog
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.subscription import Subscription
from models.video_extraction_projection import VideoExtractionProjection
from schemas.subscription.dto.sync_center_dto import SyncCenterItemDto, SyncCenterListDto, SyncCenterOverviewDto
from services import video_extraction_projection_service
from utils.site_catalog import SiteCatalog
from utils.site_icons import build_site_icon_url, resolve_site_icon_path

EXTRACTION_PREVIEW_LIMIT = 40
SITE_CATALOG_CACHE_TTL_SECONDS = 30
_site_catalog_cache_lock = Lock()
_site_catalog_cache: dict[str, dict] | None = None
_site_catalog_cache_expires_at_monotonic: float | None = None
_site_icon_url_cache: dict[str, Optional[str]] = {}
logger = logging.getLogger(__name__)


def _get_cached_site_catalog() -> dict[str, dict]:
    global _site_catalog_cache
    global _site_catalog_cache_expires_at_monotonic

    now_tick = monotonic()
    if (
        _site_catalog_cache is not None
        and _site_catalog_cache_expires_at_monotonic is not None
        and now_tick < _site_catalog_cache_expires_at_monotonic
    ):
        return _site_catalog_cache

    with _site_catalog_cache_lock:
        now_tick = monotonic()
        if (
            _site_catalog_cache is not None
            and _site_catalog_cache_expires_at_monotonic is not None
            and now_tick < _site_catalog_cache_expires_at_monotonic
        ):
            return _site_catalog_cache

        try:
            catalog = get_effective_site_catalog() or {}
        except (ValueError, TypeError, AttributeError, KeyError):
            logger.warning('Failed to load effective site catalog for extraction center icons', exc_info=True)
            catalog = _site_catalog_cache or {}

        _site_catalog_cache = catalog
        _site_icon_url_cache.clear()
        _site_catalog_cache_expires_at_monotonic = now_tick + SITE_CATALOG_CACHE_TTL_SECONDS
        return _site_catalog_cache


def _format_datetime(value: Optional[datetime]) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''


def _summarize_error(message: Optional[str]) -> Optional[str]:
    if not message:
        return None

    normalized = str(message).strip()
    if not normalized:
        return None

    lowered = normalized.lower()
    if 'extract' in lowered:
        return '提取失败'
    if 'timeout' in lowered:
        return '处理超时'
    if 'network' in lowered or 'connection' in lowered:
        return '网络异常'

    first_line = normalized.splitlines()[0].strip()
    if len(first_line) <= 80:
        return first_line
    return first_line[:77] + '...'


def _resolve_site_icon_url(site: Optional[str]) -> Optional[str]:
    normalized_site = str(site or '').strip().lower()
    if not normalized_site:
        return None

    cached_icon_url = _site_icon_url_cache.get(normalized_site)
    if normalized_site in _site_icon_url_cache:
        return cached_icon_url

    catalog = _get_cached_site_catalog()

    if normalized_site in catalog:
        site_slug = normalized_site
        catalog_entry = catalog[site_slug]
    else:
        site_slug = None
        catalog_entry = None

        for slug, info in catalog.items():
            domains = [str(domain or '').strip().lower() for domain in info.get('domains', []) if domain]
            if any(normalized_site == domain or normalized_site.endswith(f'.{domain}') for domain in domains):
                site_slug = slug
                catalog_entry = info
                break

        if not site_slug:
            site_slug = None
            catalog_entry = None
            for slug, info in catalog.items():
                aliases = [str(alias or '').strip().lower() for alias in info.get('aliases', []) if alias]
                if normalized_site in aliases:
                    site_slug = slug
                    catalog_entry = info
                    break

    icon_url = str((catalog_entry or {}).get('icon_url') or '').strip() or None
    if icon_url:
        _site_icon_url_cache[normalized_site] = icon_url
        return icon_url

    fallback_slug = site_slug or normalized_site
    if resolve_site_icon_path(fallback_slug):
        resolved_icon_url = build_site_icon_url(fallback_slug)
        _site_icon_url_cache[normalized_site] = resolved_icon_url
        return resolved_icon_url

    _site_icon_url_cache[normalized_site] = None
    return None


def _build_run_id(group_kind: str, group_value: str) -> str:
    return f'extract:{group_kind}:{group_value}'


def _derive_projection_group_key(task: CrawlTask) -> tuple[str, str]:
    payload = task.payload or {}
    run_id = payload.get('run_id')
    if run_id not in (None, ''):
        return 'run', str(run_id)

    sync_state_id = payload.get('sync_state_id')
    if sync_state_id not in (None, ''):
        return 'state', str(sync_state_id)

    return 'job', str(task.job_id)


def _resolve_task_sync_mode(task: CrawlTask) -> str:
    payload = task.payload or {}
    normalized_mode = str(payload.get('mode') or payload.get('sync_mode') or '').strip().lower()
    if normalized_mode in {'full', 'incremental'}:
        return normalized_mode

    is_extract_all = payload.get('is_extract_all')
    if is_extract_all is True:
        return 'full'

    if (
        is_extract_all is False
        or payload.get('run_id') not in (None, '')
        or payload.get('sync_state_id') not in (None, '')
    ):
        return 'incremental'

    return 'extract'


def _resolve_projection_sync_mode(
    session: Session,
    projection: VideoExtractionProjection,
    cache: dict[tuple[int, str, str], str],
) -> str:
    cache_key = (int(projection.subscription_id), str(projection.group_kind), str(projection.group_value))
    cached_mode = cache.get(cache_key)
    if cached_mode:
        return cached_mode

    tasks = session.execute(
        select(CrawlTask)
        .where(
            CrawlTask.task_type == 'video_extract',
            CrawlTask.subscription_id == projection.subscription_id,
        )
        .order_by(CrawlTask.created_at.asc(), CrawlTask.id.asc())
    ).scalars().all()

    for task in tasks:
        if _derive_projection_group_key(task) == (projection.group_kind, str(projection.group_value)):
            resolved_mode = _resolve_task_sync_mode(task)
            cache[cache_key] = resolved_mode
            return resolved_mode

    cache[cache_key] = 'extract'
    return 'extract'


def _base_projection_query(
    user_id: int,
    *,
    site_candidates: Optional[set[str]] = None,
    normalized_query: str = '',
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
        query = query.where(Subscription.name.ilike(f'%{normalized_query}%'))
    return query


def _apply_status_filter(query: Any, status: Optional[str]) -> Any:
    normalized_status = (status or '').strip().lower() or None
    if normalized_status == 'running':
        return query.where(VideoExtractionProjection.display_status == 'running')
    if normalized_status == 'queued':
        return query.where(VideoExtractionProjection.display_status == 'queued')
    if normalized_status == 'failed':
        return query.where(VideoExtractionProjection.sync_status == 'failed')
    if normalized_status == 'recent':
        return query.where(VideoExtractionProjection.display_status.notin_(['running', 'queued']))
    return query


def _apply_ordering(query: Any, status: Optional[str]) -> Any:
    normalized_status = (status or '').strip().lower() or None
    if normalized_status == 'running':
        return query.order_by(VideoExtractionProjection.locked_at.asc(), VideoExtractionProjection.subscription_id.asc())
    if normalized_status == 'queued':
        return query.order_by(VideoExtractionProjection.queued_at.asc(), VideoExtractionProjection.subscription_id.asc())
    recent_dt = func.coalesce(VideoExtractionProjection.updated_at, VideoExtractionProjection.last_success_at)
    return query.order_by(recent_dt.desc(), VideoExtractionProjection.subscription_id.desc())


def _build_item(
    session: Session,
    projection: VideoExtractionProjection,
    subscription: Subscription,
    sync_mode_cache: dict[tuple[int, str, str], str],
) -> SyncCenterItemDto:
    active_count = int(projection.pending_video_count or 0)
    processed_count = int(projection.completed_task_count or 0) + int(projection.failed_task_count or 0)
    sync_mode = _resolve_projection_sync_mode(session, projection, sync_mode_cache)

    return SyncCenterItemDto(
        run_id=_build_run_id(projection.group_kind, projection.group_value),
        subscription_id=subscription.id,
        subscription_name=subscription.name,
        subscription_avatar=subscription.avatar,
        site=projection.site,
        site_icon_url=_resolve_site_icon_url(projection.site),
        sync_mode=sync_mode,
        sync_status=projection.sync_status,
        display_status=projection.display_status,
        current_phase=projection.current_phase,
        failure_count=int(projection.failed_task_count or 0),
        last_error=projection.last_error,
        last_error_summary=_summarize_error(projection.last_error),
        last_sync_at='',
        last_success_at=_format_datetime(projection.last_success_at if projection.sync_status == 'success' else None),
        next_sync_at='',
        queued_at=_format_datetime(projection.queued_at),
        locked_at=_format_datetime(projection.locked_at),
        updated_at=_format_datetime(projection.updated_at),
        pending_video_count=active_count,
        feed_completed=active_count == 0,
        has_more_pages=False,
        videos_found=int(projection.batch_task_count or 0),
        videos_enqueued=int(projection.queued_task_count or 0),
        videos_extracted=int(projection.completed_task_count or 0),
        videos_skipped=0,
        progress_percent=int((processed_count / projection.batch_task_count) * 100) if projection.batch_task_count else 0,
        progress_label=f'{processed_count} / {projection.batch_task_count}' if projection.batch_task_count else '',
        is_deferred=False,
        defer_reason=None,
        batch_task_count=int(projection.batch_task_count or 0),
        queued_task_count=int(projection.queued_task_count or 0),
        running_task_count=int(projection.running_task_count or 0),
        completed_task_count=int(projection.completed_task_count or 0),
        failed_task_count=int(projection.failed_task_count or 0),
    )


def _ensure_projection_ready() -> None:
    video_extraction_projection_service.ensure_projection_seeded()


def get_extraction_center_overview(user_id: int) -> SyncCenterOverviewDto:
    _ensure_projection_ready()

    with get_session() as session:
        query = (
            select(
                func.coalesce(
                    func.sum(case((VideoExtractionProjection.display_status == 'running', 1), else_=0)),
                    0,
                ).label('running_count'),
                func.coalesce(
                    func.sum(case((VideoExtractionProjection.display_status == 'queued', 1), else_=0)),
                    0,
                ).label('queued_count'),
                func.coalesce(
                    func.sum(case((VideoExtractionProjection.sync_status == 'failed', 1), else_=0)),
                    0,
                ).label('failed_count'),
                func.coalesce(func.sum(VideoExtractionProjection.pending_video_count), 0).label('pending_videos'),
                func.coalesce(func.sum(VideoExtractionProjection.queued_task_count), 0).label('queue_depth'),
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


def get_extraction_dashboard_snapshot(user_id: int, *, preview_limit: int = EXTRACTION_PREVIEW_LIMIT) -> dict:
    overview = get_extraction_center_overview(user_id)
    running_count = int(overview.running_count or 0)
    queued_count = int(overview.queued_count or 0)
    running_preview = (
        list_extraction_center_items(user_id, 'running', None, None, 1, running_count).data
        if running_count > 0 else []
    )
    queued_preview = (
        list_extraction_center_items(user_id, 'queued', None, None, 1, queued_count).data
        if queued_count > 0 else []
    )
    recent_preview = list_extraction_center_items(user_id, 'recent', None, None, 1, preview_limit).data
    return {
        'overview': overview,
        'runningPreview': running_preview,
        'queuedPreview': queued_preview,
        'recentPreview': recent_preview,
    }


def list_extraction_center_items(
    user_id: int,
    status: Optional[str],
    site: Optional[str],
    query: Optional[str],
    page: int,
    page_size: int,
) -> SyncCenterListDto:
    _ensure_projection_ready()

    normalized_status = (status or '').strip().lower() or None
    normalized_site = (site or '').strip().lower() or None
    site_candidates = set(SiteCatalog.expand_site_filter_values(normalized_site)) if normalized_site else set()
    normalized_query = (query or '').strip().lower()
    start = max(0, (page - 1) * page_size)

    filtered_query = _apply_status_filter(
        _base_projection_query(
            user_id,
            site_candidates=site_candidates,
            normalized_query=normalized_query,
        ),
        normalized_status,
    )
    ordered_query = _apply_ordering(filtered_query, normalized_status)

    with get_session() as session:
        total = int(
            session.execute(
                select(func.count()).select_from(filtered_query.order_by(None).subquery())
            ).scalar()
            or 0
        )
        rows = session.execute(
            ordered_query.offset(start).limit(page_size)
        ).all()
        sync_mode_cache: dict[tuple[int, str, str], str] = {}
        items = [_build_item(session, projection, subscription, sync_mode_cache) for projection, subscription in rows]

    if normalized_status == 'queued':
        for index, item in enumerate(items, start=start + 1):
            item.queue_position = index

    return SyncCenterListDto(
        total=total,
        page=page,
        page_size=page_size,
        data=items,
    )
