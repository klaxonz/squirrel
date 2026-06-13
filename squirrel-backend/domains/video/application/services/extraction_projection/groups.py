from __future__ import annotations

from domains.subscription.domain.models.crawl_task import CrawlTask

RUNNING_TASK_STATUSES = {'leased', 'running'}
QUEUED_TASK_STATUSES = {'pending', 'retry_wait'}
FAILED_TASK_STATUSES = {'dead', 'cancelled'}
COMPLETED_TASK_STATUSES = {'succeeded'}
VIDEO_EXTRACT_TASK_TYPE = 'video_extract'
ACTIVE_PROJECTION_STATUSES = {'running', 'queued'}


def derive_group_key(task: CrawlTask) -> tuple[str, str]:
    payload = task.payload or {}
    run_id = payload.get('run_id')
    if run_id not in (None, ''):
        return 'run', str(run_id)
    sync_state_id = payload.get('sync_state_id')
    if sync_state_id not in (None, ''):
        return 'state', str(sync_state_id)
    return 'job', str(task.job_id)
