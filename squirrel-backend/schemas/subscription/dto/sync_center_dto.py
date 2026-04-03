from pydantic import BaseModel


class SyncCenterOverviewDto(BaseModel):
    running_count: int = 0
    awaiting_extract_count: int = 0
    queued_count: int = 0
    failed_count: int = 0
    due_soon_count: int = 0
    deferred_count: int = 0
    pending_videos: int = 0
    queue_depth: int = 0
    queue_messages: int = 0


class SyncCenterItemDto(BaseModel):
    run_id: str | None = None
    subscription_id: int
    subscription_name: str
    subscription_avatar: str | None = None
    site: str | None = None
    sync_mode: str = 'incremental'
    sync_status: str = 'idle'
    display_status: str = 'healthy'
    current_phase: str | None = None
    failure_count: int = 0
    last_error: str | None = None
    last_error_summary: str | None = None
    last_sync_at: str = ''
    last_success_at: str = ''
    next_sync_at: str = ''
    queued_at: str = ''
    locked_at: str = ''
    updated_at: str = ''
    pending_video_count: int = 0
    feed_completed: bool = False
    has_more_pages: bool = False
    queue_position: int | None = None
    videos_found: int = 0
    videos_enqueued: int = 0
    videos_extracted: int = 0
    videos_skipped: int = 0
    progress_percent: int = 0
    progress_label: str = ''
    is_deferred: bool = False
    defer_reason: str | None = None
    batch_task_count: int = 0
    queued_task_count: int = 0
    running_task_count: int = 0
    completed_task_count: int = 0
    failed_task_count: int = 0


class SyncCenterListDto(BaseModel):
    total: int
    page: int
    page_size: int
    data: list[SyncCenterItemDto]
