from pydantic import BaseModel


class MarkReadRequest(BaseModel):
    channel_id: str
    video_id: str
    is_read: bool


class MarkReadBatchRequest(BaseModel):
    channel_id: str = None
    direction: str
    uploaded_at: str
    is_read: bool


class DownloadChannelVideoRequest(BaseModel):
    channel_id: str
    video_id: str


class DislikeRequest(BaseModel):
    channel_id: str
    video_id: str
