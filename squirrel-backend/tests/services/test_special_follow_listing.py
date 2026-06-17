"""Tests for special-follow listing (browse keyset + search id-set).

首页"特别关注"区块请求 category=all&special=yes。由于 Meili 全局 publish_ts:desc
召回只取最新 N 条，特别关注订阅的视频可能比其他订阅旧而永远进不了召回窗口，
因此 special=yes 走 PG 直查（keyset 浏览 / 反向交集搜索），不依赖全局召回。

这些测试覆盖 PG 层的 fetch_special_follow_video_ids / fetch_special_follow_id_set：
- 只返回 is_special_followed=true 订阅名下的视频
- 排除已删除、未来（publish_date > now）、publish_date 为 null 的视频
- fan-out 去重（同一视频被多个特别关注订阅关联只算一次）
- keyset 游标分页正确
"""
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.video.application.services.listing.query import (
    fetch_special_follow_id_set,
    fetch_special_follow_video_ids,
)
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video
from infrastructure.database.base import Base


@pytest.fixture
def session_factory():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            UserSubscription.__table__,
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


def _make_video(vid, *, publish_date, deleted=False):
    return Video(
        id=vid, title=f'v{vid}', url=f'http://x/{vid}', domain='x.com',
        publish_date=publish_date, is_deleted=deleted,
    )


def _seed(session_factory):
    """Seed a scenario where special-follow subs have OLDER videos than non-special subs.

    user 1:
      - sub 10 (special)  -> videos published 5..3 days ago
      - sub 11 (NOT special) -> videos published 1 day ago (newest globally)
      - sub 12 (special, but deleted user_subscription) -> should be excluded
    """
    now = datetime.now()
    with session_factory() as s:
        # videos
        s.add_all([
            _make_video(1, publish_date=now - timedelta(days=5)),   # sub 10 special
            _make_video(2, publish_date=now - timedelta(days=4)),   # sub 10 special
            _make_video(3, publish_date=now - timedelta(days=3)),   # sub 12 special (but unsubscribed)
            _make_video(4, publish_date=now - timedelta(days=1)),   # sub 11 non-special (newest)
            _make_video(5, publish_date=now - timedelta(days=2), deleted=True),   # sub 10 special, but deleted
            _make_video(6, publish_date=now + timedelta(days=1)),   # sub 10 special, FUTURE (excluded)
            _make_video(7, publish_date=None),                       # sub 10 special, null publish_date (excluded)
            _make_video(8, publish_date=now - timedelta(days=6)),   # sub 10 special, also linked to sub 11 (fan-out)
        ])
        # subscriptions
        s.add_all([Subscription(id=10, name='specialA', type='CHANNEL'),
                   Subscription(id=11, name='normalB', type='CHANNEL'),
                   Subscription(id=12, name='specialUnsub', type='CHANNEL')])
        # user_subscriptions
        s.add_all([
            UserSubscription(user_id=1, subscription_id=10, is_special_followed=True, is_deleted=False),
            UserSubscription(user_id=1, subscription_id=11, is_special_followed=False, is_deleted=False),
            UserSubscription(user_id=1, subscription_id=12, is_special_followed=True, is_deleted=True),
        ])
        # subscription_video links
        s.add_all([
            SubscriptionVideo(subscription_id=10, video_id=1),
            SubscriptionVideo(subscription_id=10, video_id=2),
            SubscriptionVideo(subscription_id=12, video_id=3),
            SubscriptionVideo(subscription_id=11, video_id=4),
            SubscriptionVideo(subscription_id=10, video_id=5),
            SubscriptionVideo(subscription_id=10, video_id=6),
            SubscriptionVideo(subscription_id=10, video_id=7),
            SubscriptionVideo(subscription_id=10, video_id=8),
            SubscriptionVideo(subscription_id=11, video_id=8),  # fan-out: video 8 in both sub10 & sub11
        ])


def test_fetch_special_follow_video_ids_returns_only_special_published_videos(session_factory):
    """keyset 浏览：只返回 is_special_followed 订阅名下、已发布、未删除的视频，按 publish_date desc。"""
    _seed(session_factory)
    with session_factory() as s:
        ids, next_cursor = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=50)
    # Expected (user 1, special=true, not deleted, published):
    #   v2 (4d ago), v1 (5d ago), v8 (6d ago). v3 (sub12 deleted), v5 (deleted), v6 (future), v7 (null) excluded.
    assert ids == [2, 1, 8]
    # all returned < limit(50), no next page
    assert next_cursor is None


def test_fetch_special_follow_video_ids_excludes_future_and_null_and_deleted(session_factory):
    """显式断言：未来视频、null publish_date、已删除视频都被排除。"""
    _seed(session_factory)
    with session_factory() as s:
        ids, _ = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=50)
    assert 6 not in ids  # future
    assert 7 not in ids  # null publish_date
    assert 5 not in ids  # deleted video
    assert 3 not in ids  # sub 12 (user_subscription is_deleted=True)


def test_fetch_special_follow_video_ids_dedupes_fan_out(session_factory):
    """同一视频被多个特别关注订阅关联只返回一次（v8 同时在 sub10 special 和 sub11 non-special）。"""
    _seed(session_factory)
    with session_factory() as s:
        ids, _ = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=50)
    assert ids.count(8) == 1


def test_fetch_special_follow_video_ids_keyset_pagination(session_factory):
    """keyset 游标分页：limit=1 取首页，cursor 翻页取后续。"""
    _seed(session_factory)
    with session_factory() as s:
        page1, cursor1 = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=1)
        page2, cursor2 = fetch_special_follow_video_ids(s, user_id=1, cursor=cursor1, limit=1)
        page3, cursor3 = fetch_special_follow_video_ids(s, user_id=1, cursor=cursor2, limit=1)
    assert page1 == [2]   # newest (4d ago)
    assert page2 == [1]   # 5d ago
    assert page3 == [8]   # 6d ago
    # cursor1/cursor2 non-None (had more), cursor3 None (exhausted)
    assert cursor1 is not None
    assert cursor2 is not None
    assert cursor3 is None


def test_fetch_special_follow_video_ids_empty_when_no_special_subs(session_factory):
    """用户没有任何特别关注订阅 → 返回空。"""
    with session_factory() as s:
        ids, next_cursor = fetch_special_follow_video_ids(s, user_id=999, cursor=None, limit=50)
    assert ids == []
    assert next_cursor is None


def test_fetch_special_follow_id_set_returns_special_published_ids(session_factory):
    """搜索反向交集：取 id 集合，只含特别关注订阅名下的已发布视频。"""
    _seed(session_factory)
    with session_factory() as s:
        ids = fetch_special_follow_id_set(s, user_id=1)
    # same eligible set as keyset test (order may differ — set is by publish_date desc but treated as set by caller)
    assert set(ids) == {1, 2, 8}
    # excludes
    assert 6 not in ids  # future
    assert 7 not in ids  # null
    assert 3 not in ids  # unsubscribed sub


def test_fetch_special_follow_id_set_dedupes_fan_out(session_factory):
    _seed(session_factory)
    with session_factory() as s:
        ids = fetch_special_follow_id_set(s, user_id=1)
    assert ids.count(8) == 1
