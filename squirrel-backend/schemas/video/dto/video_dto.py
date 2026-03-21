from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_serializer
from sqlalchemy_to_pydantic import sqlalchemy_to_pydantic

from models.video import Video


class VideoExtractDto(BaseModel):
    url: str
    subscribed: bool
    only_extract: bool
    subscription_id: int
    sync_state_id: Optional[int] = None
    run_id: Optional[str] = None
    trigger: Optional[str] = None
    is_manual: bool = False
    is_extract_all: bool = False


class VideoDto(sqlalchemy_to_pydantic(Video)):

    subscription_id: int

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")}

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


class VideoCountDto(BaseModel):
    total: int
    preview: int
    read: int
    unread: int

class QualityOptionDto(BaseModel):
    """Single quality option for manual selection on frontend"""
    value: str  # e.g. '1080p' | '720p' | 'audio-128k'
    label: str  # display label
    height: Optional[int] = None  # for video tracks
    bandwidth: Optional[int] = None  # bps
    id: Optional[str] = None  # representation id / itag etc.
    index: Optional[int] = None  # quality index in dash.js bitrateList or hls.js levels (0-based)


class VideoUrlDto(BaseModel):
    """DTO for video URL response"""
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    mpd_url: Optional[str] = None
    qualities: Optional[List[QualityOptionDto]] = None

    class Config:
        from_attributes = True

