from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from schemas.subscription.dto.sync_center_dto import (
    SyncCenterItemDto,
    SyncCenterListDto,
    SyncCenterOverviewDto,
)
from utils import url_helper
from utils.metrics import metrics


DUE_SOON_WINDOW = timedelta(minutes=30)
DISPLAY_STATUS_RANK = {
    'running': 0,
    'queued': 1,
    'failed': 2,
    'deferred': 3,
    'scheduled': 4,
    'healthy': 5,
}


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


def _resolve_site_name(subscription: Subscription, sync_state: Optional[SubscriptionSyncState]) -> Optional[str]:
    if sync_state and sync_state.site:
        return sync_state.site
    if not subscription.url:
        return None
    try:
        return url_helper.extract_top_level_domain(subscription.url)
    except Exception:
        return None


def _resolve_display_status(
    sync_state: Optional[SubscriptionSyncState],
    *,
    now: Optional[datetime] = None,
    due_soon_threshold: timedelta = DUE_SOON_WINDOW,
) -> str:
    if not sync_state:
        return 'healthy'

    current_time = now or datetime.now()
    if sync_state.sync_status == SyncStatus.RUNNING.value:
        return 'running'
    if sync_state.sync_status == SyncStatus.QUEUED.value:
        return 'queued'
    if sync_state.sync_status == SyncStatus.FAILED.value:
        return 'failed'
    if sync_state.last_error == 'queue_backpressure':
        return 'deferred'
    if (
        sync_state.next_sync_at
        and current_time <= sync_state.next_sync_at <= current_time + due_soon_threshold
    ):
        return 'scheduled'
    return 'healthy'


def _state_time_value(sync_state: Optional[SubscriptionSyncState], display_status: str) -> datetime:
    if not sync_state:
        return datetime.min
    if display_status == 'running':
        return sync_state.locked_at or sync_state.updated_at or datetime.min
    if display_status == 'queued':
        return sync_state.queued_at or sync_state.updated_at or datetime.min
    if display_status == 'scheduled':
        return sync_state.next_sync_at or datetime.max
    return sync_state.last_sync_at or sync_state.updated_at or datetime.min


def _pick_preferred_state(
    states: list[SubscriptionSyncState],
    *,
    now: datetime,
) -> Optional[SubscriptionSyncState]:
    if not states:
        return None

    def state_key(sync_state: SubscriptionSyncState):
        display_status = _resolve_display_status(sync_state, now=now)
        rank = DISPLAY_STATUS_RANK.get(display_status, 99)
        time_value = _state_time_value(sync_state, display_status)
        if display_status == 'scheduled':
            time_key = time_value
        else:
            time_key = datetime.max - (time_value - datetime.min)
        mode_rank = 0 if sync_state.sync_mode == SyncMode.INCREMENTAL.value else 1
        return rank, time_key, mode_rank, sync_state.id

    return min(states, key=state_key)


def _build_sync_center_item(
    subscription: Subscription,
    sync_state: Optional[SubscriptionSyncState],
    *,
    now: datetime,
) -> SyncCenterItemDto:
    display_status = _resolve_display_status(sync_state, now=now)
    site_name = _resolve_site_name(subscription, sync_state)
    last_error = sync_state.last_error if sync_state else None
    is_deferred = display_status == 'deferred'

    return SyncCenterItemDto(
        subscription_id=subscription.id,
        subscription_name=subscription.name,
        subscription_avatar=subscription.avatar,
        site=site_name,
        sync_mode=sync_state.sync_mode if sync_state else SyncMode.INCREMENTAL.value,
        sync_status=sync_state.sync_status if sync_state else SyncStatus.IDLE.value,
        display_status=display_status,
        failure_count=sync_state.failure_count if sync_state else 0,
        last_error=last_error,
        last_error_summary=_summarize_error(last_error),
        last_sync_at=_format_datetime(sync_state.last_sync_at if sync_state else None),
        last_success_at=_format_datetime(sync_state.last_success_at if sync_state else None),
        next_sync_at=_format_datetime(sync_state.next_sync_at if sync_state else None),
        queued_at=_format_datetime(sync_state.queued_at if sync_state else None),
        locked_at=_format_datetime(sync_state.locked_at if sync_state else None),
        updated_at=_format_datetime(sync_state.updated_at if sync_state else None),
        pending_video_count=sync_state.pending_video_count if sync_state else 0,
        is_deferred=is_deferred,
        defer_reason='queue_backpressure' if is_deferred else None,
    )


def _load_subscription_state_rows(user_id: int):
    with get_session() as session:
        rows = session.execute(
            select(Subscription, SubscriptionSyncState)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .outerjoin(SubscriptionSyncState, SubscriptionSyncState.subscription_id == Subscription.id)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            )
            .order_by(Subscription.id.asc(), SubscriptionSyncState.updated_at.desc(), SubscriptionSyncState.id.asc())
        ).all()
        return rows


def _collect_sync_center_items(user_id: int) -> list[SyncCenterItemDto]:
    rows = _load_subscription_state_rows(user_id)
    now = datetime.now()
    grouped: dict[int, dict[str, object]] = {}

    for subscription, sync_state in rows:
        bucket = grouped.setdefault(subscription.id, {'subscription': subscription, 'states': []})
        if sync_state:
            bucket['states'].append(sync_state)

    items: list[SyncCenterItemDto] = []
    for bucket in grouped.values():
        subscription = bucket['subscription']
        states = bucket['states']
        preferred_state = _pick_preferred_state(states, now=now)
        items.append(_build_sync_center_item(subscription, preferred_state, now=now))

    return items


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

    reverse = status not in {'queued', 'scheduled'}
    if status == 'recent':
        reverse = True
    return sorted(items, key=sort_key, reverse=reverse)


def _get_queue_metrics_overview() -> tuple[int, int]:
    queue_depth = sum(
        _safe_metric_int(metrics.redis.get(key))
        for key in metrics.get_metrics_keys_by_pattern('metrics:gauge:queue.depth:*')
    )
    queue_messages = sum(
        _safe_metric_int(metrics.redis.get(key))
        for key in metrics.get_metrics_keys_by_pattern('metrics:counter:queue.messages.total:*')
    )
    return queue_depth, queue_messages


def get_sync_center_overview(user_id: int) -> SyncCenterOverviewDto:
    items = _collect_sync_center_items(user_id)
    queue_depth, queue_messages = _get_queue_metrics_overview()

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
    normalized_query = (query or '').strip().lower()

    items = _collect_sync_center_items(user_id)

    if normalized_status and normalized_status != 'recent':
        items = [item for item in items if item.display_status == normalized_status]
    if normalized_site:
        items = [item for item in items if (item.site or '').lower() == normalized_site]
    if normalized_query:
        items = [item for item in items if normalized_query in item.subscription_name.lower()]

    sorted_items = _sort_items(items, normalized_status)
    total = len(sorted_items)
    start = max(0, (page - 1) * page_size)
    end = start + page_size

    return SyncCenterListDto(
        total=total,
        page=page,
        page_size=page_size,
        data=sorted_items[start:end],
    )


def list_retry_failed_sync_items(
    user_id: int,
    site: Optional[str],
    query: Optional[str],
) -> list[SyncCenterItemDto]:
    items = _collect_sync_center_items(user_id)
    normalized_site = (site or '').strip().lower() or None
    normalized_query = (query or '').strip().lower()

    failed_items = [item for item in items if item.display_status == 'failed']
    if normalized_site:
        failed_items = [item for item in failed_items if (item.site or '').lower() == normalized_site]
    if normalized_query:
        failed_items = [item for item in failed_items if normalized_query in item.subscription_name.lower()]

    return _sort_items(failed_items, 'failed')
