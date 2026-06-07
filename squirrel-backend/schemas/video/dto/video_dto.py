from datetime import datetime

from pydantic import BaseModel, field_serializer
from sqlalchemy_to_pydantic import sqlalchemy_to_pydantic

from models.video import Video


class VideoExtractDto(BaseModel):
    url: str
    subscribed: bool
    only_extract: bool
    subscription_id: int
    sync_state_id: int | None = None
    run_id: str | None = None
    trigger: str | None = None
    is_manual: bool = False
    is_extract_all: bool = False


class VideoDto(sqlalchemy_to_pydantic(Video)):

    subscription_id: int

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")}

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: datetime | None) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


class VideoCountDto(BaseModel):
    total: int
    preview: int
    read: int
    unread: int
