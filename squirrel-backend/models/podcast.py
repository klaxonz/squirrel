from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, Text, Boolean, VARCHAR, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class PodcastChannel(Base):
    __tablename__ = "podcast_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(VARCHAR(128), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    cover_url: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    rss_url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    website_url: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    categories: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )


class PodcastEpisode(Base):
    __tablename__ = "podcast_episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(VARCHAR(128), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cover_url: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    last_position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )


class PodcastSubscription(Base):
    __tablename__ = "podcast_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )


class PodcastPlayHistory(Base):
    __tablename__ = "podcast_play_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[int] = mapped_column(Integer, default=0)
    last_played_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    is_finished: Mapped[bool] = mapped_column(Boolean, default=False)
