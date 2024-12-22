from enum import Enum
from pydantic import BaseModel


class SortBy(str, Enum):
    UPLOADED_AT = "publish_date"
    CREATED_AT = "created_at"


class DownloadVideoRequest(BaseModel):
    video_id: int
