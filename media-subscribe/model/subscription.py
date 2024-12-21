from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.types import JSON
from .links import SubscriptionVideo

if TYPE_CHECKING:
    from .video import Video


class ContentType:
    CHANNEL = "CHANNEL"
    ACTRESS = "ACTRESS"
    MOVIE = "MOVIE"
    TV_SERIES = "TV_SERIES"
    ACTOR = "ACTOR"


class Subscription(SQLModel, table=True):
    __tablename__ = "subscription"
    
    subscription_id: Optional[int] = Field(default=None, primary_key=True)
    content_type: str
    content_name: str
    content_url: Optional[str]
    avatar_url: Optional[str]
    description: Optional[str]
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

    videos: list["Video"] = Relationship(
        back_populates="subscriptions",
        link_model=SubscriptionVideo
    )