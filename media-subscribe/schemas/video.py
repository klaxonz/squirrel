from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SortBy(str, Enum):
    UPLOADED_AT = "publish_date"
    CREATED_AT = "created_at"


class DownloadVideoRequest(BaseModel):
    video_id: int


class ToggleLikeRequest(BaseModel):
    channel_id: str
    video_id: str
    is_liked: Optional[bool] = None