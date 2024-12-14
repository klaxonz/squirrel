from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship
from sqlalchemy.types import JSON
from .base import TimestampMixin
from .links import SubscriptionVideo, VideoCreator

if TYPE_CHECKING:
    from .creator import Creator
    from .subscription import Subscription

class Video(TimestampMixin, table=True):
    __tablename__ = "video"
    
    video_id: Optional[int] = Field(default=None, primary_key=True)
    video_title: str
    video_url: str = Field(sa_column_kwargs={"unique": True})
    video_description: Optional[str]
    video_duration: Optional[int]
    thumbnail_url: Optional[str]
    publish_date: Optional[datetime]
    extra_data: Optional[dict] = Field(default=None, sa_type=JSON)
    
    subscriptions: list["Subscription"] = Relationship(
        back_populates="videos",
        link_model=SubscriptionVideo
    )
    creators: list["Creator"] = Relationship(
        back_populates="videos",
        link_model=VideoCreator
    ) 