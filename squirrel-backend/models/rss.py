from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, Text, UniqueConstraint, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class RssAccount(Base, SerializerMixin):
    __tablename__ = 'rss_account'

    __table_args__ = (
        UniqueConstraint('user_id', 'provider', 'base_url', 'name', name='uix_rss_account_user_provider_url_name'),
        Index('ix_rss_account_user_provider', 'user_id', 'provider'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(120), nullable=False)
    base_url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    credential_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_entry_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(), onupdate=lambda: datetime.now())


class RssFeed(Base, SerializerMixin):
    __tablename__ = 'rss_feed'

    __table_args__ = (
        UniqueConstraint('account_id', 'external_feed_id', name='uix_rss_feed_account_external'),
        Index('ix_rss_feed_account_enabled', 'account_id', 'enabled'),
        Index('ix_rss_feed_user_title', 'user_id', 'title'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False)
    external_feed_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    feed_url: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    site_url: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_entry_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(), onupdate=lambda: datetime.now())


class RssEntry(Base, SerializerMixin):
    __tablename__ = 'rss_entry'

    __table_args__ = (
        UniqueConstraint('feed_id', 'external_entry_id', name='uix_rss_entry_feed_external'),
        Index('ix_rss_entry_feed_published', 'feed_id', 'published_at'),
        Index('ix_rss_entry_user_published', 'user_id', 'published_at'),
        Index('ix_rss_entry_user_read', 'user_id', 'is_read', 'published_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False)
    feed_id: Mapped[int] = mapped_column(Integer, nullable=False)
    external_entry_id: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(), onupdate=lambda: datetime.now())



