from datetime import datetime
from typing import Optional

from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class ContentType:
    CHANNEL = "CHANNEL"
    ACTRESS = "ACTRESS"
    MOVIE = "MOVIE"
    TV_SERIES = "TV_SERIES"
    ACTOR = "ACTOR"


class Subscription(SQLModel, table=True):
    __tablename__ = "subscription"

    id: Optional[int] = Field(default=None, primary_key=True)
    content_type: str
    content_name: str
    content_url: Optional[str]
    avatar_url: Optional[str]
    description: Optional[str]
    total_videos: Optional[int] = Field(default=0)
    is_enable: bool = Field(default=True)
    is_auto_download: bool = Field(default=False)
    is_download_all: bool = Field(default=False)
    is_extract_all: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    extra_data: Optional[dict] = Field(default=None, sa_type=JSON)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(),
        sa_column_kwargs={"onupdate": lambda: datetime.now()}
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now()
    )
