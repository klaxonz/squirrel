from collections.abc import Callable
from datetime import datetime

from domains.subscription.application.services.sync.site_icons import SiteIconResolver
from domains.subscription.interfaces.dto.dto.sync_dashboard_dto import SyncDashboardItemDto


def summarize_error(message: str | None) -> str | None:
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


def build_run_id(group_kind: str, group_value: str) -> str:
    return f'extract:{group_kind}:{group_value}'


def build_extraction_item(
    projection,
    subscription,
    *,
    sync_mode: str,
    format_datetime: Callable[[datetime | None], str],
    site_icon_resolver: SiteIconResolver,
) -> SyncDashboardItemDto:
    active_count = int(projection.pending_video_count or 0)
    processed_count = int(projection.completed_task_count or 0) + int(projection.failed_task_count or 0)

    return SyncDashboardItemDto(
        run_id=build_run_id(projection.group_kind, projection.group_value),
        subscription_id=subscription.id,
        subscription_name=subscription.name,
        subscription_avatar=subscription.avatar,
        site=projection.site,
        site_icon_url=site_icon_resolver.resolve(projection.site),
        sync_mode=sync_mode,
        sync_status=projection.sync_status,
        display_status=projection.display_status,
        current_phase=projection.current_phase,
        failure_count=int(projection.failed_task_count or 0),
        last_error=projection.last_error,
        last_error_summary=summarize_error(projection.last_error),
        last_sync_at='',
        last_success_at=format_datetime(projection.last_success_at if projection.sync_status == 'success' else None),
        next_sync_at='',
        queued_at=format_datetime(projection.queued_at),
        locked_at=format_datetime(projection.locked_at),
        updated_at=format_datetime(projection.updated_at),
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
        progress_label=f'{processed_count} / {projection.batch_task_count}' if projection.batch_task_count else '',
        is_deferred=False,
        defer_reason=None,
        batch_task_count=int(projection.batch_task_count or 0),
        queued_task_count=int(projection.queued_task_count or 0),
        running_task_count=int(projection.running_task_count or 0),
        completed_task_count=int(projection.completed_task_count or 0),
        failed_task_count=int(projection.failed_task_count or 0),
    )
