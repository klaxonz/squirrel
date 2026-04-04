from collections import defaultdict
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from core.database import get_session
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.subscription import Subscription
from schemas.subscription.dto.sync_center_dto import SyncCenterItemDto, SyncCenterListDto, SyncCenterOverviewDto
from utils.site_catalog import SiteCatalog
from utils.site_icons import build_site_icon_url, resolve_site_icon_path


RUNNING_TASK_STATUSES = {'leased', 'running'}
QUEUED_TASK_STATUSES = {'pending', 'retry_wait'}
FAILED_TASK_STATUSES = {'dead', 'cancelled'}
COMPLETED_TASK_STATUSES = {'succeeded'}


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


def _parse_sync_state_id(task: CrawlTask) -> str:
    payload = task.payload or {}
    sync_state_id = payload.get('sync_state_id')
    if sync_state_id in (None, ''):
        return f'job:{task.job_id}'
    try:
        return f'state:{int(sync_state_id)}'
    except (TypeError, ValueError):
        return f'job:{task.job_id}'


def _build_extraction_item(subscription: Subscription, tasks: list[CrawlTask]) -> SyncCenterItemDto:
    ordered_tasks = sorted(tasks, key=lambda item: (item.created_at or datetime.min, item.id))
    total_count = len(ordered_tasks)
    queued_count = sum(1 for task in ordered_tasks if task.status in QUEUED_TASK_STATUSES)
    running_count = sum(1 for task in ordered_tasks if task.status in RUNNING_TASK_STATUSES)
    completed_count = sum(1 for task in ordered_tasks if task.status in COMPLETED_TASK_STATUSES)
    failed_count = sum(1 for task in ordered_tasks if task.status in FAILED_TASK_STATUSES)
    active_count = queued_count + running_count
    processed_count = completed_count + failed_count

    started_at_values = [task.started_at for task in ordered_tasks if task.started_at]
    finished_at_values = [task.finished_at for task in ordered_tasks if task.finished_at]
    updated_at_values = [task.updated_at for task in ordered_tasks if task.updated_at]

    if running_count > 0:
        sync_status = 'running'
        display_status = 'running'
        current_phase = 'extracting'
    elif active_count > 0:
        sync_status = 'queued'
        display_status = 'queued'
        current_phase = 'queued'
    elif failed_count > 0:
        sync_status = 'failed'
        display_status = 'failed'
        current_phase = 'completed'
    else:
        sync_status = 'success'
        display_status = 'healthy'
        current_phase = 'completed'

    latest_failed_task = max(
        (task for task in ordered_tasks if task.status in FAILED_TASK_STATUSES),
        key=lambda item: (item.updated_at or datetime.min, item.id),
        default=None,
    )
    progress_percent = int((processed_count / total_count) * 100) if total_count else 0

    return SyncCenterItemDto(
        run_id=f'extract:{_parse_sync_state_id(ordered_tasks[0])}',
        subscription_id=subscription.id,
        subscription_name=subscription.name,
        subscription_avatar=subscription.avatar,
        site=ordered_tasks[0].site if ordered_tasks else None,
        site_icon_url=_resolve_site_icon_url(ordered_tasks[0].site if ordered_tasks else None),
        sync_mode='extract',
        sync_status=sync_status,
        display_status=display_status,
        current_phase=current_phase,
        failure_count=failed_count,
        last_error=latest_failed_task.last_error if latest_failed_task else None,
        last_error_summary=_summarize_error(latest_failed_task.last_error if latest_failed_task else None),
        last_sync_at='',
        last_success_at=_format_datetime(max(finished_at_values) if sync_status == 'success' and finished_at_values else None),
        next_sync_at='',
        queued_at=_format_datetime(min((task.created_at for task in ordered_tasks if task.created_at), default=None)),
        locked_at=_format_datetime(min(started_at_values) if started_at_values else None),
        updated_at=_format_datetime(max(updated_at_values) if updated_at_values else None),
        pending_video_count=active_count,
        feed_completed=active_count == 0,
        has_more_pages=False,
        videos_found=total_count,
        videos_enqueued=queued_count,
        videos_extracted=completed_count,
        videos_skipped=0,
        progress_percent=progress_percent,
        progress_label=f'{processed_count} / {total_count}' if total_count else '',
        is_deferred=False,
        defer_reason=None,
        batch_task_count=total_count,
        queued_task_count=queued_count,
        running_task_count=running_count,
        completed_task_count=completed_count,
        failed_task_count=failed_count,
    )


def _collect_extraction_items(user_id: int) -> list[SyncCenterItemDto]:
    with get_session() as session:
        rows = session.execute(
            select(Subscription, CrawlTask)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .join(CrawlTask, CrawlTask.subscription_id == Subscription.id)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
                CrawlTask.task_type == 'video_extract',
            )
            .order_by(CrawlTask.created_at.asc(), CrawlTask.id.asc())
        ).all()

    grouped: dict[tuple[int, str], dict[str, object]] = defaultdict(lambda: {'subscription': None, 'tasks': []})
    for subscription, task in rows:
        group_key = (subscription.id, _parse_sync_state_id(task))
        grouped[group_key]['subscription'] = subscription
        grouped[group_key]['tasks'].append(task)

    return [
        _build_extraction_item(group['subscription'], group['tasks'])
        for group in grouped.values()
        if group['subscription'] is not None and group['tasks']
    ]


def _sort_items(items: list[SyncCenterItemDto], status: Optional[str]) -> list[SyncCenterItemDto]:
    def parse_dt(value: str, *, fallback: datetime) -> datetime:
        if not value:
            return fallback
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return fallback

    if status == 'running':
        return sorted(items, key=lambda item: (parse_dt(item.locked_at, fallback=datetime.min), item.subscription_id))
    if status == 'queued':
        return sorted(items, key=lambda item: (parse_dt(item.queued_at, fallback=datetime.max), item.subscription_id))
    return sorted(
        items,
        key=lambda item: (
            parse_dt(item.updated_at or item.last_success_at, fallback=datetime.min),
            item.subscription_id,
        ),
        reverse=True,
    )


def get_extraction_center_overview(user_id: int) -> SyncCenterOverviewDto:
    items = _collect_extraction_items(user_id)
    return SyncCenterOverviewDto(
        running_count=sum(1 for item in items if item.display_status == 'running'),
        queued_count=sum(1 for item in items if item.display_status == 'queued'),
        failed_count=sum(1 for item in items if item.sync_status == 'failed'),
        due_soon_count=0,
        deferred_count=0,
        pending_videos=sum(item.pending_video_count for item in items),
        queue_depth=sum(item.queued_task_count for item in items),
        queue_messages=0,
    )


def list_extraction_center_items(
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

    items = _collect_extraction_items(user_id)

    if normalized_status == 'running':
        items = [item for item in items if item.display_status == 'running']
    elif normalized_status == 'queued':
        items = [item for item in items if item.display_status == 'queued']
    elif normalized_status == 'failed':
        items = [item for item in items if item.sync_status == 'failed']
    elif normalized_status == 'recent':
        items = [item for item in items if item.display_status not in {'running', 'queued'}]

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
