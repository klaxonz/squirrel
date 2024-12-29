from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel

from .links import SubscriptionVideo, VideoCreator

if TYPE_CHECKING:
    from .creator import Creator
    from .subscription import Subscription


class Video(SQLModel, table=True):
    __tablename__ = "video"

    video_id: Optional[int] = Field(default=None, primary_key=True)
    video_title: str
    video_url: str = Field(sa_column_kwargs={"unique": True})
    video_description: Optional[str]
    video_duration: Optional[int]
    thumbnail_url: Optional[str]
    publish_date: Optional[datetime]
    is_deleted: bool = Field(default=False)
    extra_data: Optional[dict] = Field(default=None, sa_type=JSON)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(),
        sa_column_kwargs={"onupdate": lambda: datetime.now()}
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now()
    )

    subscriptions: list["Subscription"] = Relationship(
        back_populates="videos",
        link_model=SubscriptionVideo
    )
    creators: list["Creator"] = Relationship(
        back_populates="videos",
        link_model=VideoCreator
    )
