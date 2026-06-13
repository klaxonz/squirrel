from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.video.domain.models.video_extraction_projection import VideoExtractionProjection

SyncModeCache = dict[tuple[int, str, str], str]


def derive_projection_group_key(task: CrawlTask) -> tuple[str, str]:
    payload = task.payload or {}
    run_id = payload.get('run_id')
    if run_id not in (None, ''):
        return 'run', str(run_id)

    sync_state_id = payload.get('sync_state_id')
    if sync_state_id not in (None, ''):
        return 'state', str(sync_state_id)

    return 'job', str(task.job_id)


def resolve_task_sync_mode(task: CrawlTask) -> str:
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


def preload_sync_mode_cache(session: Session, subscription_ids: set[int], cache: SyncModeCache) -> None:
    if not subscription_ids:
        return

    tasks = (
        session.execute(
            select(CrawlTask)
            .where(
                CrawlTask.task_type == 'video_extract',
                CrawlTask.subscription_id.in_(subscription_ids),
            )
            .order_by(CrawlTask.created_at.asc(), CrawlTask.id.asc()),
        )
        .scalars()
        .all()
    )

    for task in tasks:
        group_key = derive_projection_group_key(task)
        cache_key = (int(task.subscription_id), group_key[0], group_key[1])
        if cache_key not in cache:
            cache[cache_key] = resolve_task_sync_mode(task)


def resolve_projection_sync_mode(projection: VideoExtractionProjection, cache: SyncModeCache) -> str:
    cache_key = (int(projection.subscription_id), str(projection.group_kind), str(projection.group_value))
    cached_mode = cache.get(cache_key)
    if cached_mode:
        return cached_mode

    cache[cache_key] = 'extract'
    return 'extract'
