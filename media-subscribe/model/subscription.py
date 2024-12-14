from enum import Enum
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship
from sqlalchemy.types import JSON
from .base import TimestampMixin
from .links import SubscriptionVideo

if TYPE_CHECKING:
    from .video import Video

class ContentType(str, Enum):
    CHANNEL = "CHANNEL"
    ACTRESS = "ACTRESS"
    MOVIE = "MOVIE"
    TV_SERIES = "TV_SERIES"
    ACTOR = "ACTOR"

class Status(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class Subscription(TimestampMixin, table=True):
    __tablename__ = "subscription"
    
    subscription_id: Optional[int] = Field(default=None, primary_key=True)
    content_type: ContentType
    content_name: str
    content_url: Optional[str]
    avatar_url: Optional[str]
    description: Optional[str]
    status: Status = Field(default=Status.ACTIVE)
    extra_data: Optional[dict] = Field(default=None, sa_type=JSON)
    
    videos: list["Video"] = Relationship(
        back_populates="subscriptions",
        link_model=SubscriptionVideo
    ) 