from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship
from sqlalchemy.types import JSON

from .base import TimestampMixin
from .links import VideoCreator

if TYPE_CHECKING:
    from .video import Video

class Creator(TimestampMixin, table=True):
    __tablename__ = "creator"
    
    creator_id: Optional[int] = Field(default=None, primary_key=True)
    creator_name: str
    creator_url: Optional[str] = Field(sa_column_kwargs={"unique": True})
    avatar_url: Optional[str]
    description: Optional[str]
    extra_data: Optional[dict] = Field(default=None, sa_type=JSON)
    
    videos: list["Video"] = Relationship(
        back_populates="creators",
        link_model=VideoCreator
    ) 