from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SortBy(StrEnum):
    UPLOADED_AT = "publish_date"
    CREATED_AT = "created_at"


class VideoCategory(StrEnum):
    ALL = "all"
    READ = "read"
    UNREAD = "unread"
    PREVIEW = "preview"
    LIKED = "liked"
    LATER = "later"


class YesNoAll(StrEnum):
    ALL = "all"
    YES = "yes"
    NO = "no"


class TimeRange(StrEnum):
    ALL = "all"
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class DurationFilter(StrEnum):
    ALL = "all"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class ContentType(StrEnum):
    ALL = "all"
    CHANNEL = "CHANNEL"
    PLAYLIST = "PLAYLIST"
    ACTRESS = "ACTRESS"
    MOVIE = "MOVIE"
    TV_SERIES = "TV_SERIES"
    ACTOR = "ACTOR"


class RemoteVideoSaveRequest(BaseModel):
    site: str | None = Field(default=None, max_length=64)
    url: str = Field(..., min_length=1, max_length=2048)
    title: str = Field(..., min_length=1, max_length=512)
    thumbnail: str | None = Field(default=None, max_length=2048)
    duration: int | None = Field(default=None, ge=0)
    publish_date: str | None = None
    uploaded_at: str | None = None
    description: str | None = None
    subscriptions: list[dict[str, Any]] | None = None
    actors: list[dict[str, Any]] | None = None
