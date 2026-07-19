"""Tests for user-state listing helpers used by read/liked/later search."""

from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.user.domain.models.user import User
from domains.video.application.services.listing.query import fetch_user_state_id_set, filter_user_state_ids
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_interaction import VideoInteraction
from infrastructure.database.base import Base


@pytest.fixture
def session_factory():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Video.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            UserSubscription.__table__,
            VideoInteraction.__table__,
        ],
    )

    @contextmanager
    def _factory():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _factory


def test_fetch_user_state_id_set_returns_all_liked_video_ids(session_factory):
    now = datetime.now()
    with session_factory() as session:
        session.add_all(
            [
                VideoInteraction(
                    user_id=1,
                    video_id=video_id,
                    interaction_type=1,
                    created_at=now - timedelta(seconds=video_id),
                )
                for video_id in range(1, 5002)
            ]
        )

    with session_factory() as session:
        ids = fetch_user_state_id_set(session, user_id=1, category='liked')

    assert len(ids) == 5001
    assert ids[-1] == 5001


def test_filter_user_state_ids_honors_sensitive_toggle_without_feed_visibility(session_factory):
    now = datetime.now()
    with session_factory() as session:
        session.add(User(id=1, nickname='u1'))
        session.add_all(
            [
                Video(id=1, title='normal subscribed', url='https://v/1', publish_date=now),
                Video(id=2, title='nsfw subscribed', url='https://v/2', publish_date=now),
                Video(id=3, title='no subscription link', url='https://v/3', publish_date=now),
                Video(id=4, title='deleted', url='https://v/4', publish_date=now, is_deleted=True),
                Video(id=5, title='null publish date', url='https://v/5', publish_date=None),
                Video(id=6, title='unsubscribed', url='https://v/6', publish_date=now),
                Video(
                    id=7,
                    title='nsfw domain without subscription',
                    url='https://v/7',
                    domain='youtube.com',
                    publish_date=now,
                ),
            ]
        )
        session.add_all(
            [
                Subscription(id=10, name='normal', type='CHANNEL'),
                Subscription(id=11, name='nsfw', type='CHANNEL'),
                Subscription(id=12, name='removed', type='CHANNEL'),
            ]
        )
        session.add_all(
            [
                UserSubscription(user_id=1, subscription_id=10, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=1, subscription_id=11, is_deleted=False, is_nsfw=True),
                UserSubscription(user_id=1, subscription_id=12, is_deleted=True, is_nsfw=False),
            ]
        )
        session.add_all(
            [
                SubscriptionVideo(subscription_id=10, video_id=1),
                SubscriptionVideo(subscription_id=11, video_id=2),
                SubscriptionVideo(subscription_id=12, video_id=6),
            ]
        )

    with session_factory() as session:
        ids = filter_user_state_ids(
            session,
            recalled_ids=[1, 2, 3, 4, 5, 6, 7, 999],
            user_id=1,
            show_nsfw=False,
            subscription_id=None,
            nsfw='all',
            domains=None,
            content_type='all',
            special='all',
        )

    assert ids == [1, 3, 5, 6]


def test_filter_user_state_ids_keeps_sensitive_likes_when_toggle_enabled(session_factory):
    now = datetime.now()
    with session_factory() as session:
        session.add(User(id=1, nickname='u1'))
        session.add_all(
            [
                Video(id=1, title='normal subscribed', url='https://v/1', publish_date=now),
                Video(id=2, title='nsfw subscribed', url='https://v/2', publish_date=now),
                Video(id=3, title='no subscription link', url='https://v/3', publish_date=now),
                Video(id=4, title='deleted', url='https://v/4', publish_date=now, is_deleted=True),
                Video(id=5, title='null publish date', url='https://v/5', publish_date=None),
                Video(id=6, title='unsubscribed', url='https://v/6', publish_date=now),
                Video(
                    id=7,
                    title='nsfw domain without subscription',
                    url='https://v/7',
                    domain='youtube.com',
                    publish_date=now,
                ),
            ]
        )
        session.add_all(
            [
                Subscription(id=10, name='normal', type='CHANNEL'),
                Subscription(id=11, name='nsfw', type='CHANNEL'),
                Subscription(id=12, name='removed', type='CHANNEL'),
            ]
        )
        session.add_all(
            [
                UserSubscription(user_id=1, subscription_id=10, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=1, subscription_id=11, is_deleted=False, is_nsfw=True),
                UserSubscription(user_id=1, subscription_id=12, is_deleted=True, is_nsfw=False),
            ]
        )
        session.add_all(
            [
                SubscriptionVideo(subscription_id=10, video_id=1),
                SubscriptionVideo(subscription_id=11, video_id=2),
                SubscriptionVideo(subscription_id=12, video_id=6),
            ]
        )

    with session_factory() as session:
        ids = filter_user_state_ids(
            session,
            recalled_ids=[1, 2, 3, 4, 5, 6, 7, 999],
            user_id=1,
            show_nsfw=True,
            subscription_id=None,
            nsfw='all',
            domains=None,
            content_type='all',
            special='all',
        )

    assert ids == [1, 2, 3, 5, 6, 7]


def test_filter_user_state_ids_applies_explicit_nsfw_filter_without_feed_visibility(session_factory):
    now = datetime.now()
    with session_factory() as session:
        session.add(User(id=1, nickname='u1'))
        session.add_all(
            [
                Video(id=1, title='normal subscribed', url='https://v/1', publish_date=now),
                Video(id=2, title='nsfw subscribed', url='https://v/2', publish_date=now),
                Video(
                    id=3,
                    title='nsfw domain without subscription',
                    url='https://v/3',
                    domain='youtube.com',
                    publish_date=now,
                ),
            ]
        )
        session.add_all(
            [
                Subscription(id=10, name='normal', type='CHANNEL'),
                Subscription(id=11, name='nsfw', type='CHANNEL'),
            ]
        )
        session.add_all(
            [
                UserSubscription(user_id=1, subscription_id=10, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=1, subscription_id=11, is_deleted=False, is_nsfw=True),
            ]
        )
        session.add_all(
            [
                SubscriptionVideo(subscription_id=10, video_id=1),
                SubscriptionVideo(subscription_id=11, video_id=2),
            ]
        )

    with session_factory() as session:
        ids = filter_user_state_ids(
            session,
            recalled_ids=[1, 2, 3],
            user_id=1,
            show_nsfw=True,
            subscription_id=None,
            nsfw='yes',
            domains=None,
            content_type='all',
            special='all',
        )

    assert ids == [2, 3]


def test_filter_user_state_ids_applies_site_domains_without_subscription_visibility(session_factory):
    now = datetime.now()
    with session_factory() as session:
        session.add_all(
            [
                Video(id=1, title='bilibili liked', url='https://v/1', domain='bilibili.com', publish_date=now),
                Video(id=2, title='youtube liked', url='https://v/2', domain='youtube.com', publish_date=now),
                Video(id=3, title='missing domain liked', url='https://v/3', publish_date=now),
                Video(id=4, title='bilibili deleted', url='https://v/4', domain='bilibili.com', is_deleted=True),
            ]
        )

    with session_factory() as session:
        ids = filter_user_state_ids(
            session,
            recalled_ids=[1, 2, 3, 4],
            user_id=1,
            show_nsfw=True,
            subscription_id=None,
            nsfw='all',
            domains=['BILIBILI.COM'],
            content_type='all',
            special='all',
        )

    assert ids == [1]
