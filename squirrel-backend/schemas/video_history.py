from typing import List, Optional

from pydantic import BaseModel


class UpdateHistoryRequest(BaseModel):
    video_id: str
    channel_id: str
    watch_duration: int
    last_position: int
    total_duration: int


class ClearHistoryRequest(BaseModel):
    video_ids: Optional[List[str]] = None
