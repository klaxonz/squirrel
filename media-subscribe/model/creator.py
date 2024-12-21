from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.types import JSON

from .base import TimestampMixin
from .links import VideoCreator

if TYPE_CHECKING:
    from .video import Video

class Creator(SQLModel, table=True):
    __tablename__ = "creator"
    
    creator_id: Optional[int] = Field(default=None, primary_key=True)
    creator_name: str
    creator_url: Optional[str] = Field(sa_column_kwargs={"unique": True})
    avatar_url: Optional[str]
    description: Optional[str]
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
        back_populates="creators",
        link_model=VideoCreator
    ) 