from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from schemas.subscription.dto.sync_center_dto import (
    SyncCenterItemDto,
    SyncCenterListDto,
    SyncCenterOverviewDto,
)
from services.subscription_sync_progress import build_progress_snapshot
from utils.metrics import metrics
from utils.site_catalog import SiteCatalog


DUE_SOON_WINDOW = timedelta(minutes=30)


def _format_datetime(value: Optional[datetime]) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''


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


def _sort_items(items: list[SyncCenterItemDto], status: Optional[str]) -> list[SyncCenterItemDto]:
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
            return parse_dt(item.queued_at, fallback=datetime.max), item.subscription_id
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
    items = _collect_projection_items(user_id)
    queue_depth, queue_messages = _queue_metrics_overview()

    return SyncCenterOverviewDto(
        running_count=sum(1 for item in items if item.display_status == 'running'),
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

    items = _collect_projection_items(user_id)
    if normalized_status and normalized_status != 'recent':
        items = [item for item in items if item.display_status == normalized_status]
    if site_candidates:
        items = [item for item in items if (item.site or '').lower() in site_candidates]
    if normalized_query:
        items = [item for item in items if normalized_query in item.subscription_name.lower()]

    sorted_items = _sort_items(items, normalized_status)
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


def list_retry_failed_sync_items(user_id: int, site: Optional[str], query: Optional[str]) -> list[SyncCenterItemDto]:
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
