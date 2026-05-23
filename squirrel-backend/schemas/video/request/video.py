from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SortBy(str, Enum):
    UPLOADED_AT = "publish_date"
    CREATED_AT = "created_at"


class RemoteVideoSaveRequest(BaseModel):
    site: Optional[str] = Field(default=None, max_length=64)
    url: str = Field(..., min_length=1, max_length=2048)
    title: str = Field(..., min_length=1, max_length=512)
    thumbnail: Optional[str] = Field(default=None, max_length=2048)
    duration: Optional[int] = Field(default=None, ge=0)
    publish_date: Optional[str] = None
    uploaded_at: Optional[str] = None
    description: Optional[str] = None
    subscriptions: Optional[list[dict[str, Any]]] = None
    actors: Optional[list[dict[str, Any]]] = None
