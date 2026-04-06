import logging
from datetime import datetime, timedelta
from threading import Lock
from time import monotonic
from typing import Optional

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import OperationalError

from core.database import get_session
from core.site_config_manager import get_effective_site_catalog
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from schemas.subscription.dto.sync_center_dto import (
    SyncCenterItemDto,
    SyncCenterListDto,
    SyncCenterOverviewDto,
)
from services.crawl_tasks.models import CrawlTaskStatus
from services.subscription_sync_progress import ACTIVE_EXTRACTION_PHASES, TERMINAL_STATUSES, build_progress_snapshot
from services.subscription_sync_run_service import SyncEventType
from services.crawl_tasks.task_types import subscription_sync_task_types
from utils.metrics import metrics
from utils.site_catalog import SiteCatalog
from utils.site_icons import build_site_icon_url, resolve_site_icon_path


DUE_SOON_WINDOW = timedelta(minutes=30)
FEED_RECENT_PHASES = {'extracting', 'finalizing', 'completed'}
FEED_HANDOFF_EVENT_TYPES = {'phase_changed', 'continued'}
FEED_HANDOFF_PHASES = {'extracting', 'finalizing'}
RUNTIME_REFRESH_INTERVAL_SECONDS = 30
SYNC_CENTER_PREVIEW_LIMIT = 40
SYNC_CENTER_RECENT_SCAN_MULTIPLIER = 4
SYNC_CENTER_RECENT_SCAN_MAX = 200
_runtime_refresh_lock = Lock()
_last_runtime_refresh_monotonic: float | None = None

# 服务端缓存：记录上一轮 snapshot 返回过的 recent run_id，用于计算新增的已完成运行
_recent_run_snapshot_cache: dict[int, set[str]] = {}

logger = logging.getLogger(__name__)


def _format_datetime(value: Optional[datetime]) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        try:
            return datetime.strptime(normalized, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None


def _safe_metric_int(value) -> int:
    if value in (None, ''):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _summarize_error(message: Optional[str]) -> Optional[str]:
    if not message:
        return None

    normalized = str(message).strip()
    if not normalized:
        return None

    lowered = normalized.lower()
    mapping = {
        'queue_backpressure': '队列积压，已延后',
        'stale_running_timeout': '同步超时，状态已回收',
        'stale_queued_missing_message': '队列消息丢失，状态已回收',
        'site_disabled': '站点已禁用',
        'no_subscribers': '没有可用订阅者',
    }
    if normalized in mapping:
        return mapping[normalized]

    if 'cookie' in lowered and ('expired' in lowered or 'invalid' in lowered or 'login' in lowered):
        return 'Cookie 可能已失效'
    if 'forbidden' in lowered or '403' in lowered:
        return '请求被拒绝'
    if 'timeout' in lowered:
        return '请求超时'
    if 'extract' in lowered:
        return '解析失败'
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

    catalog = get_effective_site_catalog()

    if normalized_site in catalog:
        site_slug = normalized_site
        catalog_entry = catalog[site_slug]
    else:
        site_slug, catalog_entry = SiteCatalog.find_site_by_domain(normalized_site)
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
        return icon_url

    fallback_slug = site_slug or normalized_site
    if resolve_site_icon_path(fallback_slug):
        return build_site_icon_url(fallback_slug)

    return None


def _resolve_display_status(current_status: Optional[str], next_sync_at: Optional[datetime]) -> str:
    status = str(current_status or '').strip().lower()
    now = datetime.now()
    if status == 'running':
        return 'running'
    if status == 'queued':
        return 'queued'
    if status in {'failed', 'timeout'}:
        return 'failed'
    if status == 'deferred':
        return 'deferred'
    if next_sync_at and now <= next_sync_at <= now + DUE_SOON_WINDOW:
        return 'scheduled'
    return 'healthy'


def _is_feed_running_item(item: SyncCenterItemDto) -> bool:
    return item.display_status == 'running' and not item.feed_completed


def _is_awaiting_extract_item(item: SyncCenterItemDto) -> bool:
    return item.display_status == 'running' and item.feed_completed


def _queue_metrics_overview() -> tuple[int, int]:
    queue_depth = sum(
        _safe_metric_int(metrics.redis.get(key))
        for key in metrics.get_metrics_keys_by_pattern('metrics:gauge:queue.depth:*')
    )
    queue_messages = sum(
        _safe_metric_int(metrics.redis.get(key))
        for key in metrics.get_metrics_keys_by_pattern('metrics:counter:queue.messages.total:*')
    )
    return queue_depth, queue_messages


def _refresh_runtime_sync_health(*, force: bool = False) -> None:
    global _last_runtime_refresh_monotonic

    now_tick = monotonic()
    if not force and _last_runtime_refresh_monotonic is not None:
        if now_tick - _last_runtime_refresh_monotonic < RUNTIME_REFRESH_INTERVAL_SECONDS:
            return

    with _runtime_refresh_lock:
        now_tick = monotonic()
        if not force and _last_runtime_refresh_monotonic is not None:
            if now_tick - _last_runtime_refresh_monotonic < RUNTIME_REFRESH_INTERVAL_SECONDS:
                return

        from services import subscription_sync_state_service

        subscription_sync_state_service.reconcile_terminal_drained_sync_states()
        subscription_sync_state_service.recover_stale_queued_sync_states()
        subscription_sync_state_service.recover_stale_running_sync_states()
        subscription_sync_state_service.reconcile_retry_wait_run_projections()
        _last_runtime_refresh_monotonic = now_tick


def _base_projection_query(user_id: int):
    return (
        select(Subscription, SubscriptionSyncSubscriptionProjection, SubscriptionSyncRunProjection)
        .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
        .outerjoin(
            SubscriptionSyncSubscriptionProjection,
            SubscriptionSyncSubscriptionProjection.subscription_id == Subscription.id,
        )
        .outerjoin(
            SubscriptionSyncRunProjection,
            SubscriptionSyncRunProjection.run_id == SubscriptionSyncSubscriptionProjection.latest_run_id,
        )
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            Subscription.is_deleted.is_(False),
        )
    )


def _projection_status_expr():
    return func.coalesce(SubscriptionSyncSubscriptionProjection.current_status, '')


def _projection_phase_expr():
    return func.coalesce(
        SubscriptionSyncRunProjection.current_phase,
        SubscriptionSyncSubscriptionProjection.current_phase,
        '',
    )


def _projection_pending_videos_expr():
    return func.coalesce(
        SubscriptionSyncSubscriptionProjection.pending_video_count,
        SubscriptionSyncRunProjection.pending_video_count,
        0,
    )


def _apply_projection_filters(query, *, status: Optional[str] = None, site_candidates: Optional[set[str]] = None, normalized_query: str = ''):
    clauses = _projection_filter_clauses(
        status=status,
        site_candidates=site_candidates,
        normalized_query=normalized_query,
    )
    if clauses:
        query = query.where(*clauses)
    return query


def _projection_filter_clauses(*, status: Optional[str] = None, site_candidates: Optional[set[str]] = None, normalized_query: str = ''):
    clauses = []
    normalized_status = (status or '').strip().lower() or None
    current_status = _projection_status_expr()
    current_phase = _projection_phase_expr()
    if normalized_status == 'running':
        clauses.extend([
            current_status == 'running',
            current_phase.notin_(ACTIVE_EXTRACTION_PHASES),
        ])
    elif normalized_status == 'queued':
        clauses.append(current_status == 'queued')
    elif normalized_status == 'failed':
        clauses.append(current_status.in_({'failed', 'timeout'}))
    elif normalized_status == 'deferred':
        clauses.append(current_status == 'deferred')
    elif normalized_status == 'scheduled':
        now = datetime.now()
        clauses.extend([
            current_status.notin_({'running', 'queued', 'failed', 'timeout', 'deferred'}),
            SubscriptionSyncSubscriptionProjection.next_sync_at.is_not(None),
            SubscriptionSyncSubscriptionProjection.next_sync_at >= now,
            SubscriptionSyncSubscriptionProjection.next_sync_at <= now + DUE_SOON_WINDOW,
        ])

    if site_candidates:
        clauses.append(SubscriptionSyncRunProjection.site.in_(site_candidates))
    if normalized_query:
        clauses.append(Subscription.name.ilike(f'%{normalized_query}%'))

    return clauses


def _apply_projection_ordering(query, status: Optional[str]):
    normalized_status = (status or '').strip().lower() or None
    if normalized_status == 'running':
        return query.order_by(
            SubscriptionSyncRunProjection.started_at.asc(),
            Subscription.id.asc(),
        )
    if normalized_status == 'queued':
        return query.order_by(
            SubscriptionSyncRunProjection.queued_at.asc(),
            Subscription.id.asc(),
        )
    if normalized_status == 'scheduled':
        return query.order_by(
            SubscriptionSyncSubscriptionProjection.next_sync_at.asc(),
            Subscription.id.asc(),
        )
    if normalized_status == 'recent':
        return query.order_by(
            func.coalesce(
                SubscriptionSyncSubscriptionProjection.updated_at,
                SubscriptionSyncRunProjection.updated_at,
                SubscriptionSyncRunProjection.started_at,
                SubscriptionSyncRunProjection.queued_at,
                SubscriptionSyncSubscriptionProjection.last_sync_at,
                SubscriptionSyncSubscriptionProjection.last_success_at,
            ).desc(),
            Subscription.id.desc(),
        )
    return query.order_by(
        func.coalesce(
            SubscriptionSyncSubscriptionProjection.last_sync_at,
            SubscriptionSyncSubscriptionProjection.updated_at,
            SubscriptionSyncRunProjection.updated_at,
        ).desc(),
        Subscription.id.desc(),
    )


def _count_projection_rows(session, query) -> int:
    return int(
        session.execute(
            select(func.count()).select_from(query.order_by(None).subquery())
        ).scalar()
        or 0
    )


def _load_projection_rows(
    session,
    *,
    user_id: int,
    filter_status: Optional[str] = None,
    order_status: Optional[str] = None,
    site_candidates: Optional[set[str]] = None,
    normalized_query: str = '',
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    limit: Optional[int] = None,
):
    filtered_query = _apply_projection_filters(
        _base_projection_query(user_id),
        status=filter_status,
        site_candidates=site_candidates,
        normalized_query=normalized_query,
    )
    ordered_query = _apply_projection_ordering(filtered_query, order_status if order_status is not None else filter_status)

    if page is not None and page_size is not None:
        start = max(0, (page - 1) * page_size)
        ordered_query = ordered_query.offset(start).limit(page_size)
    elif limit is not None:
        ordered_query = ordered_query.limit(limit)

    return session.execute(ordered_query).all()


def _load_projection_items(
    session,
    *,
    user_id: int,
    filter_status: Optional[str] = None,
    order_status: Optional[str] = None,
    site_candidates: Optional[set[str]] = None,
    normalized_query: str = '',
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    limit: Optional[int] = None,
) -> list[SyncCenterItemDto]:
    rows = _load_projection_rows(
        session,
        user_id=user_id,
        filter_status=filter_status,
        order_status=order_status,
        site_candidates=site_candidates,
        normalized_query=normalized_query,
        page=page,
        page_size=page_size,
        limit=limit,
    )
    return [
        _build_sync_center_item(subscription, subscription_projection, run_projection)
        for subscription, subscription_projection, run_projection in rows
    ]


def _build_sync_center_item(
    subscription: Subscription,
    subscription_projection: Optional[SubscriptionSyncSubscriptionProjection],
    run_projection: Optional[SubscriptionSyncRunProjection],
) -> SyncCenterItemDto:
    current_status = subscription_projection.current_status if subscription_projection else None
    next_sync_at = subscription_projection.next_sync_at if subscription_projection else None
    display_status = _resolve_display_status(current_status, next_sync_at)
    sync_mode = (run_projection.sync_mode if run_projection and run_projection.sync_mode else 'incremental')
    sync_status = current_status or (run_projection.status if run_projection else 'idle')
    pending_video_count = (
        subscription_projection.pending_video_count
        if subscription_projection
        else (run_projection.pending_video_count if run_projection else 0)
    )
    last_error = (
        subscription_projection.last_error_message
        if subscription_projection and subscription_projection.last_error_message
        else (run_projection.error_message if run_projection else None)
    )
    progress_snapshot = build_progress_snapshot(
        status=run_projection.status if run_projection else current_status,
        current_phase=run_projection.current_phase if run_projection else (subscription_projection.current_phase if subscription_projection else None),
        videos_found=run_projection.videos_found if run_projection else 0,
        videos_enqueued=run_projection.videos_enqueued if run_projection else 0,
        videos_extracted=run_projection.videos_extracted if run_projection else 0,
        pending_video_count=pending_video_count,
    )

    return SyncCenterItemDto(
        run_id=run_projection.run_id if run_projection else None,
        subscription_id=subscription.id,
        subscription_name=subscription.name,
        subscription_avatar=subscription.avatar,
        site=(run_projection.site if run_projection and run_projection.site else None),
        site_icon_url=_resolve_site_icon_url(run_projection.site if run_projection else None),
        sync_mode=sync_mode,
        sync_status=sync_status,
        display_status=display_status,
        current_phase=run_projection.current_phase if run_projection else (subscription_projection.current_phase if subscription_projection else None),
        failure_count=(run_projection.failure_count if run_projection else 0),
        last_error=last_error,
        last_error_summary=_summarize_error(last_error),
        last_sync_at=_format_datetime(subscription_projection.last_sync_at if subscription_projection else None),
        last_success_at=_format_datetime(subscription_projection.last_success_at if subscription_projection else None),
        next_sync_at=_format_datetime(next_sync_at),
        queued_at=_format_datetime(run_projection.queued_at if run_projection else None),
        locked_at=_format_datetime(run_projection.started_at if run_projection else None),
        updated_at=_format_datetime(subscription_projection.updated_at if subscription_projection else (run_projection.updated_at if run_projection else None)),
        pending_video_count=pending_video_count,
        feed_completed=bool(progress_snapshot['feed_completed']),
        has_more_pages=False,
        videos_found=run_projection.videos_found if run_projection else 0,
        videos_enqueued=run_projection.videos_enqueued if run_projection else 0,
        videos_extracted=run_projection.videos_extracted if run_projection else 0,
        videos_skipped=run_projection.videos_skipped if run_projection else 0,
        progress_percent=int(progress_snapshot['progress_percent']),
        progress_label=str(progress_snapshot['progress_label']),
        is_deferred=display_status == 'deferred',
        defer_reason='queue_backpressure' if display_status == 'deferred' else None,
    )


def _collect_projection_items(
    user_id: int,
    *,
    status: Optional[str] = None,
    site_candidates: Optional[set[str]] = None,
    normalized_query: str = '',
) -> list[SyncCenterItemDto]:
    with get_session() as session:
        return _load_projection_items(
            session,
            user_id=user_id,
            filter_status=status,
            site_candidates=site_candidates,
            normalized_query=normalized_query,
        )


def _query_queued_task_rank_map(
    session,
    user_id: int,
    items: list[SyncCenterItemDto],
) -> tuple[dict[int, int], dict[int, int]]:
    subscription_ids = sorted({item.subscription_id for item in items})
    if not subscription_ids:
        return {}, {}

    priority_order = case(
        (CrawlTask.priority == 'manual', 3),
        (CrawlTask.priority == 'normal', 2),
        (CrawlTask.priority == 'low', 1),
        else_=0,
    )

    queued_task_rows = session.execute(
        select(CrawlTask.id, CrawlTask.subscription_id)
        .join(UserSubscription, UserSubscription.subscription_id == CrawlTask.subscription_id)
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            CrawlTask.task_type.in_(subscription_sync_task_types()),
            CrawlTask.subscription_id.in_(subscription_ids),
            CrawlTask.status.in_([CrawlTaskStatus.PENDING.value, CrawlTaskStatus.RETRY_WAIT.value]),
        )
        .order_by(
            priority_order.desc(),
            CrawlTask.next_run_at.asc(),
            CrawlTask.created_at.asc(),
            CrawlTask.id.asc(),
        )
    ).all()

    from services.crawl_dispatcher.service import CrawlDispatcherService

    candidate_task_ids = session.execute(
        CrawlDispatcherService()._build_candidate_query(datetime.now())
    ).scalars().all()

    queued_task_map = {int(task_id): int(subscription_id) for task_id, subscription_id in queued_task_rows}
    candidate_subscription_ids: list[int] = []
    for task_id in candidate_task_ids:
        subscription_id = queued_task_map.get(int(task_id))
        if subscription_id is None or subscription_id in candidate_subscription_ids:
            continue
        candidate_subscription_ids.append(subscription_id)

    queued_subscription_ids = [
        int(subscription_id)
        for _, subscription_id in queued_task_rows
    ]

    candidate_rank_map: dict[int, int] = {}
    for subscription_id in candidate_subscription_ids:
        if subscription_id in candidate_rank_map:
            continue
        candidate_rank_map[subscription_id] = len(candidate_rank_map) + 1

    backlog_rank_map: dict[int, int] = {}
    for subscription_id in queued_subscription_ids:
        if subscription_id in backlog_rank_map:
            continue
        backlog_rank_map[subscription_id] = len(backlog_rank_map) + 1

    return candidate_rank_map, backlog_rank_map


def _load_queued_task_rank_map(user_id: int, items: list[SyncCenterItemDto]) -> tuple[dict[int, int], dict[int, int]]:
    try:
        with get_session() as session:
            return _query_queued_task_rank_map(session, user_id, items)
    except OperationalError:
        logger.warning('Falling back to projection queue ordering because crawl_task lookup is unavailable')
        return {}, {}


def _serialize_feed_recent_run(
    run_projection: SubscriptionSyncRunProjection,
    subscription: Subscription,
    feed_completed_at: Optional[datetime],
) -> dict:
    progress_snapshot = build_progress_snapshot(
        status=run_projection.status,
        current_phase=run_projection.current_phase,
        videos_found=run_projection.videos_found,
        videos_enqueued=run_projection.videos_enqueued,
        videos_extracted=run_projection.videos_extracted,
        pending_video_count=run_projection.pending_video_count,
    )
    return {
        'run_id': run_projection.run_id,
        'subscription_id': subscription.id,
        'subscription_name': subscription.name,
        'subscription_avatar': subscription.avatar,
        'site': run_projection.site,
        'site_icon_url': _resolve_site_icon_url(run_projection.site),
        'sync_mode': run_projection.sync_mode,
        'trigger': run_projection.trigger,
        'status': run_projection.status,
        'current_phase': run_projection.current_phase,
        'request_id': run_projection.request_id,
        'trace_id': run_projection.trace_id,
        'queued_at': _format_datetime(run_projection.queued_at),
        'started_at': _format_datetime(run_projection.started_at),
        'finished_at': _format_datetime(run_projection.finished_at),
        'duration_ms': run_projection.duration_ms,
        'failure_count': run_projection.failure_count,
        'error_type': run_projection.error_type,
        'error_message': run_projection.error_message,
        'videos_found': run_projection.videos_found,
        'videos_enqueued': run_projection.videos_enqueued,
        'videos_extracted': run_projection.videos_extracted,
        'videos_skipped': run_projection.videos_skipped,
        'pending_video_count': run_projection.pending_video_count,
        'feed_completed': progress_snapshot['feed_completed'],
        'progress_percent': progress_snapshot['progress_percent'],
        'progress_label': progress_snapshot['progress_label'],
        'feed_completed_at': _format_datetime(feed_completed_at),
        'last_event_at': _format_datetime(run_projection.last_event_at),
    }


def _load_feed_completed_at_map(session, run_ids: list[str]) -> dict[str, datetime]:
    if not run_ids:
        return {}

    handoff_rows = session.execute(
        select(
            SubscriptionSyncEvent.stream_id,
            func.max(SubscriptionSyncEvent.occurred_at),
        )
        .where(
            SubscriptionSyncEvent.stream_id.in_(run_ids),
            SubscriptionSyncEvent.event_type.in_(FEED_HANDOFF_EVENT_TYPES),
            SubscriptionSyncEvent.event_phase.in_(FEED_HANDOFF_PHASES),
        )
        .group_by(SubscriptionSyncEvent.stream_id)
    ).all()

    feed_completed_at_map = {
        str(stream_id): occurred_at
        for stream_id, occurred_at in handoff_rows
        if stream_id and occurred_at
    }

    unresolved_run_ids = [run_id for run_id in run_ids if run_id not in feed_completed_at_map]
    if not unresolved_run_ids:
        return feed_completed_at_map

    completed_rows = session.execute(
        select(
            SubscriptionSyncEvent.stream_id,
            func.max(SubscriptionSyncEvent.occurred_at),
        )
        .where(
            SubscriptionSyncEvent.stream_id.in_(unresolved_run_ids),
            SubscriptionSyncEvent.event_type == SyncEventType.COMPLETED,
            SubscriptionSyncEvent.event_phase == 'completed',
        )
        .group_by(SubscriptionSyncEvent.stream_id)
    ).all()

    for stream_id, occurred_at in completed_rows:
        if stream_id and occurred_at:
            feed_completed_at_map[str(stream_id)] = occurred_at

    return feed_completed_at_map


def _sort_items(
    items: list[SyncCenterItemDto],
    status: Optional[str],
    *,
    queued_candidate_rank_map: Optional[dict[int, int]] = None,
    queued_backlog_rank_map: Optional[dict[int, int]] = None,
) -> list[SyncCenterItemDto]:
    def parse_dt(value: str, *, fallback: datetime) -> datetime:
        if not value:
            return fallback
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return fallback

    def recent_dt(item: SyncCenterItemDto) -> datetime:
        candidates = [
            parse_dt(item.updated_at, fallback=datetime.min),
            parse_dt(item.locked_at, fallback=datetime.min),
            parse_dt(item.queued_at, fallback=datetime.min),
            parse_dt(item.last_sync_at, fallback=datetime.min),
            parse_dt(item.last_success_at, fallback=datetime.min),
        ]
        return max(candidates)

    def sort_key(item: SyncCenterItemDto):
        if status == 'running':
            return parse_dt(item.locked_at, fallback=datetime.min), item.subscription_id
        if status == 'queued':
            candidate_rank = (queued_candidate_rank_map or {}).get(item.subscription_id)
            if candidate_rank is not None:
                return 0, candidate_rank, datetime.min, item.subscription_id
            backlog_rank = (queued_backlog_rank_map or {}).get(item.subscription_id)
            if backlog_rank is not None:
                return 1, backlog_rank, datetime.min, item.subscription_id
            return 2, 0, parse_dt(item.queued_at, fallback=datetime.max), item.subscription_id
        if status == 'scheduled':
            return parse_dt(item.next_sync_at, fallback=datetime.max), item.subscription_id
        if status == 'recent':
            return recent_dt(item), item.subscription_id
        return parse_dt(item.last_sync_at, fallback=datetime.min), item.subscription_id

    reverse = status not in {'queued', 'scheduled', 'running'}
    if status == 'recent':
        reverse = True
    return sorted(items, key=sort_key, reverse=reverse)


def get_sync_center_overview(user_id: int) -> SyncCenterOverviewDto:
    queue_depth, queue_messages = _queue_metrics_overview()

    now = datetime.now()
    current_status = _projection_status_expr()
    current_phase = _projection_phase_expr()
    pending_videos = _projection_pending_videos_expr()

    with get_session() as session:
        row = session.execute(
            select(
                func.coalesce(func.sum(case((
                    and_(
                        current_status == 'running',
                        current_phase.notin_(ACTIVE_EXTRACTION_PHASES),
                    ),
                    1,
                ), else_=0)), 0).label('running_count'),
                func.coalesce(func.sum(case((
                    and_(
                        current_status == 'running',
                        current_phase.in_(ACTIVE_EXTRACTION_PHASES),
                    ),
                    1,
                ), else_=0)), 0).label('awaiting_extract_count'),
                func.coalesce(func.sum(case(((current_status == 'queued'), 1), else_=0)), 0).label('queued_count'),
                func.coalesce(func.sum(case(((current_status.in_({'failed', 'timeout'})), 1), else_=0)), 0).label('failed_count'),
                func.coalesce(func.sum(case((
                    and_(
                        current_status.notin_({'running', 'queued', 'failed', 'timeout', 'deferred'}),
                        SubscriptionSyncSubscriptionProjection.next_sync_at.is_not(None),
                        SubscriptionSyncSubscriptionProjection.next_sync_at >= now,
                        SubscriptionSyncSubscriptionProjection.next_sync_at <= now + DUE_SOON_WINDOW,
                    ),
                    1,
                ), else_=0)), 0).label('due_soon_count'),
                func.coalesce(func.sum(case(((current_status == 'deferred'), 1), else_=0)), 0).label('deferred_count'),
                func.coalesce(func.sum(pending_videos), 0).label('pending_videos'),
            )
            .select_from(Subscription)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .outerjoin(
                SubscriptionSyncSubscriptionProjection,
                SubscriptionSyncSubscriptionProjection.subscription_id == Subscription.id,
            )
            .outerjoin(
                SubscriptionSyncRunProjection,
                SubscriptionSyncRunProjection.run_id == SubscriptionSyncSubscriptionProjection.latest_run_id,
            )
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            )
        ).one()

    return SyncCenterOverviewDto(
        running_count=int(row.running_count or 0),
        awaiting_extract_count=int(row.awaiting_extract_count or 0),
        queued_count=int(row.queued_count or 0),
        failed_count=int(row.failed_count or 0),
        due_soon_count=int(row.due_soon_count or 0),
        deferred_count=int(row.deferred_count or 0),
        pending_videos=int(row.pending_videos or 0),
        queue_depth=queue_depth,
        queue_messages=queue_messages,
    )


def list_sync_center_items(
    user_id: int,
    status: Optional[str],
    site: Optional[str],
    query: Optional[str],
    page: int,
    page_size: int,
) -> SyncCenterListDto:
    normalized_status = (status or '').strip().lower() or None
    normalized_site = (site or '').strip().lower() or None
    site_candidates = set(SiteCatalog.expand_site_filter_values(normalized_site)) if normalized_site else set()
    normalized_query = (query or '').strip().lower()

    with get_session() as session:
        if normalized_status == 'queued':
            queued_items = _load_projection_items(
                session,
                user_id=user_id,
                filter_status='queued',
                site_candidates=site_candidates,
                normalized_query=normalized_query,
            )
            try:
                queued_candidate_rank_map, queued_backlog_rank_map = _query_queued_task_rank_map(
                    session,
                    user_id,
                    queued_items,
                )
            except OperationalError:
                logger.warning('Falling back to projection queue ordering because crawl_task lookup is unavailable')
                queued_candidate_rank_map, queued_backlog_rank_map = {}, {}
            sorted_items = _sort_items(
                queued_items,
                'queued',
                queued_candidate_rank_map=queued_candidate_rank_map,
                queued_backlog_rank_map=queued_backlog_rank_map,
            )
            total = len(sorted_items)
            start = max(0, (page - 1) * page_size)
            end = start + page_size
            paged_items = sorted_items[start:end]
        else:
            query_status = normalized_status if normalized_status != 'recent' else None
            filtered_query = _apply_projection_filters(
                _base_projection_query(user_id),
                status=query_status,
                site_candidates=site_candidates,
                normalized_query=normalized_query,
            )
            total = _count_projection_rows(session, filtered_query)
            paged_items = _load_projection_items(
                session,
                user_id=user_id,
                filter_status=query_status,
                order_status=normalized_status,
                site_candidates=site_candidates,
                normalized_query=normalized_query,
                page=page,
                page_size=page_size,
            )

    if normalized_status == 'queued':
        for index, item in enumerate(paged_items, start=start + 1):
            item.queue_position = index

    return SyncCenterListDto(
        total=total,
        page=page,
        page_size=page_size,
        data=paged_items,
    )


def get_feed_dashboard_snapshot(
    user_id: int,
    site: Optional[str],
    query: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    recent_limit: int = SYNC_CENTER_PREVIEW_LIMIT,
) -> dict:
    normalized_site = (site or '').strip().lower() or None
    site_candidates = set(SiteCatalog.expand_site_filter_values(normalized_site)) if normalized_site else set()
    normalized_query = (query or '').strip().lower()
    parsed_from = _parse_datetime(date_from)
    parsed_to = _parse_datetime(date_to)
    resolved_recent_limit = max(1, int(recent_limit or SYNC_CENTER_PREVIEW_LIMIT))
    recent_scan_limit = min(
        max(resolved_recent_limit * SYNC_CENTER_RECENT_SCAN_MULTIPLIER, resolved_recent_limit),
        SYNC_CENTER_RECENT_SCAN_MAX,
    )

    queue_depth, queue_messages = _queue_metrics_overview()
    current_status = _projection_status_expr()
    current_phase = _projection_phase_expr()
    pending_videos = _projection_pending_videos_expr()
    now = datetime.now()

    with get_session() as session:
        overview_row = session.execute(
            select(
                func.coalesce(func.sum(case((
                    and_(
                        current_status == 'running',
                        current_phase.notin_(ACTIVE_EXTRACTION_PHASES),
                    ),
                    1,
                ), else_=0)), 0).label('running_count'),
                func.coalesce(func.sum(case((
                    and_(
                        current_status == 'running',
                        current_phase.in_(ACTIVE_EXTRACTION_PHASES),
                    ),
                    1,
                ), else_=0)), 0).label('awaiting_extract_count'),
                func.coalesce(func.sum(case(((current_status == 'queued'), 1), else_=0)), 0).label('queued_count'),
                func.coalesce(func.sum(case(((current_status.in_({'failed', 'timeout'})), 1), else_=0)), 0).label('failed_count'),
                func.coalesce(func.sum(case((
                    and_(
                        current_status.notin_({'running', 'queued', 'failed', 'timeout', 'deferred'}),
                        SubscriptionSyncSubscriptionProjection.next_sync_at.is_not(None),
                        SubscriptionSyncSubscriptionProjection.next_sync_at >= now,
                        SubscriptionSyncSubscriptionProjection.next_sync_at <= now + DUE_SOON_WINDOW,
                    ),
                    1,
                ), else_=0)), 0).label('due_soon_count'),
                func.coalesce(func.sum(case(((current_status == 'deferred'), 1), else_=0)), 0).label('deferred_count'),
                func.coalesce(func.sum(pending_videos), 0).label('pending_videos'),
            )
            .select_from(Subscription)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .outerjoin(
                SubscriptionSyncSubscriptionProjection,
                SubscriptionSyncSubscriptionProjection.subscription_id == Subscription.id,
            )
            .outerjoin(
                SubscriptionSyncRunProjection,
                SubscriptionSyncRunProjection.run_id == SubscriptionSyncSubscriptionProjection.latest_run_id,
            )
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            )
            .where(*_projection_filter_clauses(site_candidates=site_candidates, normalized_query=normalized_query))
        ).one()

        running_preview = _load_projection_items(
            session,
            user_id=user_id,
            filter_status='running',
            site_candidates=site_candidates,
            normalized_query=normalized_query,
            limit=int(overview_row.running_count or 0),
        )

        queued_preview = _load_projection_items(
            session,
            user_id=user_id,
            filter_status='queued',
            site_candidates=site_candidates,
            normalized_query=normalized_query,
            limit=int(overview_row.queued_count or 0),
        )
        try:
            queued_candidate_rank_map, queued_backlog_rank_map = _query_queued_task_rank_map(
                session,
                user_id,
                queued_preview,
            )
        except OperationalError:
            logger.warning('Falling back to projection queue ordering because crawl_task lookup is unavailable')
            queued_candidate_rank_map, queued_backlog_rank_map = {}, {}
        queued_preview = _sort_items(
            queued_preview,
            'queued',
            queued_candidate_rank_map=queued_candidate_rank_map,
            queued_backlog_rank_map=queued_backlog_rank_map,
        )
        for index, item in enumerate(queued_preview, start=1):
            item.queue_position = index

        recent_query = (
            select(SubscriptionSyncRunProjection, Subscription)
            .join(Subscription, Subscription.id == SubscriptionSyncRunProjection.subscription_id)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .join(
                SubscriptionSyncSubscriptionProjection,
                SubscriptionSyncSubscriptionProjection.subscription_id == SubscriptionSyncRunProjection.subscription_id,
            )
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
                SubscriptionSyncSubscriptionProjection.latest_run_id == SubscriptionSyncRunProjection.run_id,
                or_(
                    SubscriptionSyncRunProjection.status.in_({'success', 'failed', 'deferred', 'timeout'}),
                    and_(
                        SubscriptionSyncRunProjection.status == 'running',
                        SubscriptionSyncRunProjection.current_phase.in_(FEED_RECENT_PHASES),
                    ),
                ),
            )
        )
        if site_candidates:
            recent_query = recent_query.where(SubscriptionSyncRunProjection.site.in_(site_candidates))
        if normalized_query:
            recent_query = recent_query.where(Subscription.name.ilike(f'%{normalized_query}%'))
        if parsed_from:
            recent_query = recent_query.where(SubscriptionSyncRunProjection.last_event_at >= parsed_from)
        if parsed_to:
            recent_query = recent_query.where(SubscriptionSyncRunProjection.last_event_at <= parsed_to)
        recent_query = recent_query.order_by(SubscriptionSyncRunProjection.last_event_at.desc()).limit(recent_scan_limit)

        recent_rows = session.execute(recent_query).all()
        feed_completed_at_map = _load_feed_completed_at_map(
            session,
            [run_projection.run_id for run_projection, _ in recent_rows if run_projection and run_projection.run_id],
        )

    recent_rows = sorted(
        recent_rows,
        key=lambda row: (
            feed_completed_at_map.get(row[0].run_id)
            or row[0].finished_at
            or row[0].last_event_at
            or row[0].started_at
            or datetime.min,
            row[0].run_id,
        ),
        reverse=True,
    )
    recent_runs = [
        _serialize_feed_recent_run(run_projection, subscription, feed_completed_at_map.get(run_projection.run_id))
        for run_projection, subscription in recent_rows
    ][:resolved_recent_limit]

    # 计算新增的已完成运行（上一轮未返回过的）
    previous_run_ids = _recent_run_snapshot_cache.get(user_id, set())
    current_run_ids = {run['run_id'] for run in recent_runs}
    newly_completed = [
        run for run in recent_runs
        if run['run_id'] not in previous_run_ids
    ][:5]

    # 更新缓存为当前轮次的 run_id 集合
    _recent_run_snapshot_cache[user_id] = current_run_ids

    overview = SyncCenterOverviewDto(
        running_count=int(overview_row.running_count or 0),
        awaiting_extract_count=int(overview_row.awaiting_extract_count or 0),
        queued_count=int(overview_row.queued_count or 0),
        failed_count=int(overview_row.failed_count or 0),
        due_soon_count=int(overview_row.due_soon_count or 0),
        deferred_count=int(overview_row.deferred_count or 0),
        pending_videos=int(overview_row.pending_videos or 0),
        queue_depth=queue_depth,
        queue_messages=queue_messages,
    )

    return {
        'overview': overview,
        'runningPreview': running_preview,
        'queuedPreview': queued_preview,
        'recentRuns': recent_runs,
        'recentlyCompletedRuns': newly_completed,
    }


def list_retry_failed_sync_items(user_id: int, site: Optional[str], query: Optional[str]) -> list[SyncCenterItemDto]:
    normalized_site = (site or '').strip().lower() or None
    site_candidates = set(SiteCatalog.expand_site_filter_values(normalized_site)) if normalized_site else set()
    normalized_query = (query or '').strip().lower()
    items = _collect_projection_items(
        user_id,
        status='failed',
        site_candidates=site_candidates,
        normalized_query=normalized_query,
    )
    failed_items = [item for item in items if item.display_status == 'failed']

    return _sort_items(failed_items, 'failed')
