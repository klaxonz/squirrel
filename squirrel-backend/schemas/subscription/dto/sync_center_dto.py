from pydantic import BaseModel


class SyncCenterOverviewDto(BaseModel):
    running_count: int = 0
    queued_count: int = 0
    failed_count: int = 0
    due_soon_count: int = 0
    deferred_count: int = 0
    pending_videos: int = 0
    queue_depth: int = 0
    queue_messages: int = 0


class SyncCenterItemDto(BaseModel):
    subscription_id: int
    subscription_name: str
    subscription_avatar: str | None = None
    site: str | None = None
    sync_mode: str = 'incremental'
    sync_status: str = 'idle'
    display_status: str = 'healthy'
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
    is_deferred: bool = False
    defer_reason: str | None = None


class SyncCenterListDto(BaseModel):
    total: int
    page: int
    page_size: int
    data: list[SyncCenterItemDto]
