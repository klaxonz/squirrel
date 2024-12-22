from typing import Optional
from datetime import datetime

from sqlalchemy import Column, DateTime, Text
from sqlmodel import SQLModel, Field, Relationship
from typing import List


class PodcastChannelBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    author: Optional[str] = None
    cover_url: Optional[str] = None
    rss_url: str = Field(unique=True)
    website_url: Optional[str] = None
    language: Optional[str] = None
    categories: Optional[str] = None
    last_updated: Optional[datetime] = None


class PodcastChannel(PodcastChannelBase, table=True):
    __tablename__ = "podcast_channels"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(sa_column=Column(DateTime, nullable=False, default=datetime.now))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    )

    # Relationships
    episodes: List["PodcastEpisode"] = Relationship(back_populates="channel")
    subscription: Optional["PodcastSubscription"] = Relationship(back_populates="channel")


class PodcastEpisodeBase(SQLModel):
    channel_id: int = Field(foreign_key="podcast_channels.id")
    title: str = Field(index=True)
    description: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    audio_url: str
    duration: Optional[int] = None
    published_at: Optional[datetime] = None
    cover_url: Optional[str] = None
    is_read: bool = Field(default=False)
    last_position: int = Field(default=0)


class PodcastEpisode(PodcastEpisodeBase, table=True):
    __tablename__ = "podcast_episodes"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(sa_column=Column(DateTime, nullable=False, default=datetime.now))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    )

    # Relationships
    channel: PodcastChannel = Relationship(back_populates="episodes")
    play_history: List["PodcastPlayHistory"] = Relationship(back_populates="episode")


class PodcastSubscription(SQLModel, table=True):
    __tablename__ = "podcast_subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(foreign_key="podcast_channels.id")
    created_at: datetime = Field(sa_column=Column(DateTime, nullable=False, default=datetime.now))

    # Relationships
    channel: PodcastChannel = Relationship(back_populates="subscription")


class PodcastPlayHistory(SQLModel, table=True):
    __tablename__ = "podcast_play_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    episode_id: int = Field(foreign_key="podcast_episodes.id")
    position: int = Field(default=0)  # 播放位置（秒）
    duration: int = Field(default=0)  # 总时长（秒）
    last_played_at: datetime = Field(default_factory=datetime.now)
    is_finished: bool = Field(default=False)  # 是否播放完成（进度超过90%）

    # Relationships
    episode: PodcastEpisode = Relationship(back_populates="play_history")
