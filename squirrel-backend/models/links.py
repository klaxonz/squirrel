from datetime import datetime

from sqlmodel import SQLModel, Field


class SubscriptionVideo(SQLModel, table=True):
    __tablename__ = "subscription_video"

    subscription_id: int = Field(primary_key=True)
    video_id: int = Field(primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now()
    )


class VideoCreator(SQLModel, table=True):
    __tablename__ = "video_creator"

    video_id: int = Field(primary_key=True)
    creator_id: int = Field(primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now()
    )
