import logging
from datetime import datetime, timedelta
from threading import Lock
from time import monotonic
from typing import Optional

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import OperationalError

from core.database import get_session
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
from services.subscription_sync_progress import build_progress_snapshot
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

    catalog = SiteCatalog.get_catalog() or {}

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


def _collect_projection_items(user_id: int) -> list[SyncCenterItemDto]:
    with get_session() as session:
        rows = session.execute(_base_projection_query(user_id)).all()

    return [
        _build_sync_center_item(subscription, subscription_projection, run_projection)
        for subscription, subscription_projection, run_projection in rows
    ]


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
    _refresh_runtime_sync_health()
    items = _collect_projection_items(user_id)
    queue_depth, queue_messages = _queue_metrics_overview()

    return SyncCenterOverviewDto(
        running_count=sum(1 for item in items if _is_feed_running_item(item)),
        awaiting_extract_count=sum(1 for item in items if _is_awaiting_extract_item(item)),
        queued_count=sum(1 for item in items if item.display_status == 'queued'),
        failed_count=sum(1 for item in items if item.display_status == 'failed'),
        due_soon_count=sum(1 for item in items if item.display_status == 'scheduled'),
        deferred_count=sum(1 for item in items if item.display_status == 'deferred'),
        pending_videos=sum(item.pending_video_count for item in items),
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

    _refresh_runtime_sync_health()
    items = _collect_projection_items(user_id)
    if normalized_status == 'running':
        items = [item for item in items if _is_feed_running_item(item)]
    elif normalized_status and normalized_status != 'recent':
        items = [item for item in items if item.display_status == normalized_status]
    if site_candidates:
        items = [item for item in items if (item.site or '').lower() in site_candidates]
    if normalized_query:
        items = [item for item in items if normalized_query in item.subscription_name.lower()]

    queued_candidate_rank_map = None
    queued_backlog_rank_map = None
    if normalized_status == 'queued':
        queued_candidate_rank_map, queued_backlog_rank_map = _load_queued_task_rank_map(user_id, items)
    sorted_items = _sort_items(
        items,
        normalized_status,
        queued_candidate_rank_map=queued_candidate_rank_map,
        queued_backlog_rank_map=queued_backlog_rank_map,
    )
    total = len(sorted_items)
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    paged_items = sorted_items[start:end]

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
) -> dict:
    normalized_site = (site or '').strip().lower() or None
    site_candidates = set(SiteCatalog.expand_site_filter_values(normalized_site)) if normalized_site else set()
    normalized_query = (query or '').strip().lower()
    parsed_from = _parse_datetime(date_from)
    parsed_to = _parse_datetime(date_to)

    _refresh_runtime_sync_health()
    with get_session() as session:
        rows = session.execute(_base_projection_query(user_id)).all()
        items = [
            _build_sync_center_item(subscription, subscription_projection, run_projection)
            for subscription, subscription_projection, run_projection in rows
        ]

        if site_candidates:
            items = [item for item in items if (item.site or '').lower() in site_candidates]
        if normalized_query:
            items = [item for item in items if normalized_query in item.subscription_name.lower()]

        running_preview = _sort_items(
            [item for item in items if _is_feed_running_item(item)],
            'running',
        )[:6]

        queued_preview = [item for item in items if item.display_status == 'queued']
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
        )[:12]
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
    )[:9]
    recent_runs = [
        _serialize_feed_recent_run(run_projection, subscription, feed_completed_at_map.get(run_projection.run_id))
        for run_projection, subscription in recent_rows
    ]

    # 计算新增的已完成运行（上一轮未返回过的）
    previous_run_ids = _recent_run_snapshot_cache.get(user_id, set())
    current_run_ids = {run['run_id'] for run in recent_runs}
    newly_completed = [
        run for run in recent_runs
        if run['run_id'] not in previous_run_ids
    ][:5]

    # 更新缓存为当前轮次的 run_id 集合
    _recent_run_snapshot_cache[user_id] = current_run_ids

    queue_depth, queue_messages = _queue_metrics_overview()

    overview = SyncCenterOverviewDto(
        running_count=sum(1 for item in items if _is_feed_running_item(item)),
        awaiting_extract_count=sum(1 for item in items if _is_awaiting_extract_item(item)),
        queued_count=sum(1 for item in items if item.display_status == 'queued'),
        failed_count=sum(1 for item in items if item.display_status == 'failed'),
        due_soon_count=sum(1 for item in items if item.display_status == 'scheduled'),
        deferred_count=sum(1 for item in items if item.display_status == 'deferred'),
        pending_videos=sum(item.pending_video_count for item in items),
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
    _refresh_runtime_sync_health()
    items = _collect_projection_items(user_id)
    normalized_site = (site or '').strip().lower() or None
    site_candidates = set(SiteCatalog.expand_site_filter_values(normalized_site)) if normalized_site else set()
    normalized_query = (query or '').strip().lower()

    failed_items = [item for item in items if item.display_status == 'failed']
    if site_candidates:
        failed_items = [item for item in failed_items if (item.site or '').lower() in site_candidates]
    if normalized_query:
        failed_items = [item for item in failed_items if normalized_query in item.subscription_name.lower()]

    return _sort_items(failed_items, 'failed')
