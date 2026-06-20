"""UserSubscription junction table - owned by subscription domain."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from infrastructure.database.base import Base

if TYPE_CHECKING:
    from domains.subscription.domain.models.subscription import Subscription


def _user_subscription_subscription_join():
    from domains.subscription.domain.models.subscription import Subscription

    return Subscription.id == foreign(UserSubscription.subscription_id)


class UserSubscription(Base):
    __tablename__ = 'user_subscription'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('subscription.id', ondelete='CASCADE'), nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_nsfw: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_special_followed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    subscription: Mapped[Subscription] = relationship(
        'Subscription',
        primaryjoin=_user_subscription_subscription_join,
        back_populates='user_subscriptions',
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint('user_id', 'subscription_id', name='uix_user_subscription'),
        Index('ix_user_subscription_user_id', 'user_id'),
        Index('ix_user_subscription_subscription_id', 'subscription_id'),
        Index('ix_user_subscription_is_deleted', 'is_deleted'),
        Index('ix_user_subscription_user_deleted_nsfw', 'user_id', 'is_deleted', 'is_nsfw'),
        Index('ix_user_subscription_user_deleted_special', 'user_id', 'is_deleted', 'is_special_followed'),
        Index('ix_user_subscription_sub_user_deleted', 'subscription_id', 'user_id', 'is_deleted'),
    )
