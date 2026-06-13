from __future__ import annotations

from datetime import datetime

from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.video.application.services.extraction_projection.groups import (
    COMPLETED_TASK_STATUSES,
    FAILED_TASK_STATUSES,
    QUEUED_TASK_STATUSES,
    RUNNING_TASK_STATUSES,
)


def compute_projection_snapshot(tasks: list[CrawlTask]) -> dict[str, object]:
    total_count = len(tasks)
    queued_count = sum(1 for task in tasks if task.status in QUEUED_TASK_STATUSES)
    running_count = sum(1 for task in tasks if task.status in RUNNING_TASK_STATUSES)
    completed_count = sum(1 for task in tasks if task.status in COMPLETED_TASK_STATUSES)
    failed_count = sum(1 for task in tasks if task.status in FAILED_TASK_STATUSES)
    active_count = queued_count + running_count

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
        (task for task in tasks if task.status in FAILED_TASK_STATUSES),
        key=lambda item: (item.updated_at or datetime.min, item.id),
        default=None,
    )

    queued_at = min((task.created_at for task in tasks if task.created_at), default=None)
    locked_at = min((task.started_at for task in tasks if task.started_at), default=None)
    updated_at = max((task.updated_at for task in tasks if task.updated_at), default=None)
    last_success_at = max(
        (task.finished_at for task in tasks if task.status in COMPLETED_TASK_STATUSES and task.finished_at),
        default=None,
    )
    first_task = tasks[0] if tasks else None

    return {
        'site': first_task.site if first_task else None,
        'sync_status': sync_status,
        'display_status': display_status,
        'current_phase': current_phase,
        'last_error': latest_failed_task.last_error if latest_failed_task else None,
        'queued_at': queued_at,
        'locked_at': locked_at,
        'last_success_at': last_success_at if sync_status == 'success' else None,
        'pending_video_count': active_count,
        'batch_task_count': total_count,
        'queued_task_count': queued_count,
        'running_task_count': running_count,
        'completed_task_count': completed_count,
        'failed_task_count': failed_count,
        'updated_at': updated_at or datetime.now(),
    }
