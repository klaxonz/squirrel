"""Tests for per-subscription listing (channel detail "local" tab).

频道详情页请求 subscription_id=X&category=all,用于列出该订阅下已解析的视频。
原先走 Meili 全局 publish_ts:desc 召回(最多 _MAX_RECALL_ROUNDSx(page_size*2) 条)
再用 subscription_id 在 PG 侧过滤——指定订阅的视频一旦比其他订阅旧,或未被索引,
就永远进不了召回窗口,导致"本地"列表即使解析了上百条也只显示寥寥几条。

现改走 PG keyset 直查 fetch_subscription_video_ids,与 fetch_special_follow_video_ids 同构。

这些测试覆盖 PG 层 fetch_subscription_video_ids:
- 只返回指定 subscription_id 名下的视频
- 归属校验:用户未订阅该 subscription_id → 返回空(防越权)
- 排除已删除、未来(publish_date > now)、publish_date 为 null 的视频
- fan-out 去重(同一视频被多个订阅关联只算一次)
- category='preview' 只取未来视频
- keyset 游标分页正确
"""
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.video.application.services.listing.query import fetch_subscription_video_ids
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
    """Seed a channel whose videos are OLDER than another subscription's.

    user 1:
      - sub 10 -> videos published 5..3 days ago (the channel we query)
      - sub 11 -> videos published 1 day ago (newest globally, NOT sub 10)
      - sub 12 (user_subscription deleted) -> should be excluded (ownership)
    user 2:
      - sub 20 -> videos (must NOT leak into user 1's query for sub 10)
    """
    now = datetime.now()
    with session_factory() as s:
        s.add_all([
            _make_video(1, publish_date=now - timedelta(days=5)),   # sub 10
            _make_video(2, publish_date=now - timedelta(days=4)),   # sub 10
            _make_video(3, publish_date=now - timedelta(days=3)),   # sub 12 (unsubscribed)
            _make_video(4, publish_date=now - timedelta(days=1)),   # sub 11 (newest globally, not sub 10)
            _make_video(5, publish_date=now - timedelta(days=2), deleted=True),   # sub 10 deleted
            _make_video(6, publish_date=now + timedelta(days=1)),   # sub 10 future
            _make_video(7, publish_date=None),                       # sub 10 null publish_date
            _make_video(8, publish_date=now - timedelta(days=6)),   # sub 10 + sub 11 (fan-out)
            _make_video(9, publish_date=now - timedelta(days=7)),   # sub 20 (user 2)
        ])
        s.add_all([Subscription(id=10, name='chanA', type='CHANNEL'),
                   Subscription(id=11, name='chanB', type='CHANNEL'),
                   Subscription(id=12, name='unsub', type='CHANNEL'),
                   Subscription(id=20, name='user2chan', type='CHANNEL')])
        s.add_all([
            UserSubscription(user_id=1, subscription_id=10, is_deleted=False),
            UserSubscription(user_id=1, subscription_id=11, is_deleted=False),
            UserSubscription(user_id=1, subscription_id=12, is_deleted=True),
            UserSubscription(user_id=2, subscription_id=20, is_deleted=False),
        ])
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
            SubscriptionVideo(subscription_id=20, video_id=9),
        ])


def test_fetch_returns_only_specified_subscription_published_videos(session_factory):
    """keyset 浏览:只返回 sub 10 名下、已发布、未删除的视频,按 publish_date desc。"""
    _seed(session_factory)
    with session_factory() as s:
        ids, next_cursor = fetch_subscription_video_ids(
            s, user_id=1, subscription_id=10, cursor=None, limit=50,
        )
    # sub 10 eligible (not deleted, published): v2 (4d), v1 (5d), v8 (6d).
    # v3 (sub 12), v4 (sub 11), v5 (deleted), v6 (future), v7 (null), v9 (user 2) excluded.
    assert ids == [2, 1, 8]
    assert next_cursor is None  # all returned < limit(50)


def test_fetch_excludes_future_and_null_and_deleted(session_factory):
    _seed(session_factory)
    with session_factory() as s:
        ids, _ = fetch_subscription_video_ids(
            s, user_id=1, subscription_id=10, cursor=None, limit=50,
        )
    assert 6 not in ids  # future
    assert 7 not in ids  # null publish_date
    assert 5 not in ids  # deleted video
    assert 3 not in ids  # sub 12 (user_subscription is_deleted=True)
    assert 4 not in ids  # sub 11, different subscription
    assert 9 not in ids  # user 2's subscription


def test_fetch_enforces_ownership(session_factory):
    """用户 2 查询 sub 10(用户 1 的订阅)→ 返回空(防越权)。"""
    _seed(session_factory)
    with session_factory() as s:
        ids, next_cursor = fetch_subscription_video_ids(
            s, user_id=2, subscription_id=10, cursor=None, limit=50,
        )
    assert ids == []
    assert next_cursor is None


def test_fetch_dedupes_fan_out(session_factory):
    """同一视频被多个订阅关联只返回一次(v8 同时在 sub10 和 sub11)。"""
    _seed(session_factory)
    with session_factory() as s:
        ids, _ = fetch_subscription_video_ids(
            s, user_id=1, subscription_id=10, cursor=None, limit=50,
        )
    assert ids.count(8) == 1


def test_fetch_keyset_pagination(session_factory):
    """keyset 游标分页:limit=1 取首页,cursor 翻页取后续。"""
    _seed(session_factory)
    with session_factory() as s:
        page1, cursor1 = fetch_subscription_video_ids(
            s, user_id=1, subscription_id=10, cursor=None, limit=1,
        )
        page2, cursor2 = fetch_subscription_video_ids(
            s, user_id=1, subscription_id=10, cursor=cursor1, limit=1,
        )
        page3, cursor3 = fetch_subscription_video_ids(
            s, user_id=1, subscription_id=10, cursor=cursor2, limit=1,
        )
    assert page1 == [2]   # newest (4d ago)
    assert page2 == [1]   # 5d ago
    assert page3 == [8]   # 6d ago
    assert cursor1 is not None
    assert cursor2 is not None
    assert cursor3 is None  # exhausted


def test_fetch_empty_when_subscription_has_no_videos(session_factory):
    """订阅没有任何视频 → 返回空。"""
    with session_factory() as s:
        s.add(Subscription(id=99, name='empty', type='CHANNEL'))
        s.add(UserSubscription(user_id=1, subscription_id=99, is_deleted=False))
    with session_factory() as s:
        ids, next_cursor = fetch_subscription_video_ids(
            s, user_id=1, subscription_id=99, cursor=None, limit=50,
        )
    assert ids == []
    assert next_cursor is None


def test_fetch_preview_category_returns_only_future_videos(session_factory):
    """category='preview' 只取未来视频(publish_date > now)。"""
    _seed(session_factory)
    with session_factory() as s:
        ids, next_cursor = fetch_subscription_video_ids(
            s, user_id=1, subscription_id=10, cursor=None, limit=50, category='preview',
        )
    # sub 10 future videos: only v6
    assert ids == [6]
    assert next_cursor is None
