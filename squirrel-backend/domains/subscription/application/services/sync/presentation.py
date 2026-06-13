from datetime import datetime
from typing import Any

from domains.subscription.interfaces.dto.dto.sync_dashboard_dto import SyncDashboardItemDto
from domains.subscription.application.services.core.sync.constants import DUE_SOON_WINDOW


def summarize_error(message: str | None) -> str | None:
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


def resolve_display_status(current_status: str | None, next_sync_at: datetime | None) -> str:
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


def sort_items(
    items: list[SyncDashboardItemDto],
    status: str | None,
    *,
    queued_candidate_rank_map: dict[int, int] | None = None,
    queued_backlog_rank_map: dict[int, int] | None = None,
) -> list[SyncDashboardItemDto]:
    def parse_dt(value: str, *, default_value: datetime) -> datetime:
        if not value:
            return default_value
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return default_value

    def recent_dt(item: SyncDashboardItemDto) -> datetime:
        candidates = [
            parse_dt(item.updated_at, default_value=datetime.min),
            parse_dt(item.locked_at, default_value=datetime.min),
            parse_dt(item.queued_at, default_value=datetime.min),
            parse_dt(item.last_sync_at, default_value=datetime.min),
            parse_dt(item.last_success_at, default_value=datetime.min),
        ]
        return max(candidates)

    def sort_key(item: SyncDashboardItemDto) -> Any:
        if status == 'running':
            return parse_dt(item.locked_at, default_value=datetime.min), item.subscription_id
        if status == 'queued':
            candidate_rank = (queued_candidate_rank_map or {}).get(item.subscription_id)
            if candidate_rank is not None:
                return 0, candidate_rank, datetime.min, item.subscription_id
            backlog_rank = (queued_backlog_rank_map or {}).get(item.subscription_id)
            if backlog_rank is not None:
                return 1, backlog_rank, datetime.min, item.subscription_id
            return 2, 0, parse_dt(item.queued_at, default_value=datetime.max), item.subscription_id
        if status == 'scheduled':
            return parse_dt(item.next_sync_at, default_value=datetime.max), item.subscription_id
        if status == 'recent':
            return recent_dt(item), item.subscription_id
        return parse_dt(item.last_sync_at, default_value=datetime.min), item.subscription_id

    reverse = status not in {'queued', 'scheduled', 'running'}
    if status == 'recent':
        reverse = True
    return sorted(items, key=sort_key, reverse=reverse)
