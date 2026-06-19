"""Tests for special-follow listing with sort_by=created_at (抓取日期排序).

覆盖"按抓取日期排序"在 PG 直查分支的行为:
- sort_by=created_at 时按 Video.created_at DESC 排序(而非 publish_date)
- 游标 key 为 'c'(created),与 publish_date 路径的 'p' 隔离
- 切换排序键时老游标(不同 key)decode 失效 → 回首页
- publish_date 的"排除未来视频"过滤与排序键无关,始终生效
"""

from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.video.application.services.listing.query import fetch_special_follow_video_ids
from domains.video.application.services.search.meili_indexer import (
    _CURSOR_KEY_CREATED,
    _CURSOR_KEY_PUBLISH,
    decode_cursor,
    decode_cursor_for_key,
    encode_cursor,
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


def _make_video(vid, *, publish_date, created_at, deleted=False):
    """显式指定 publish_date 与 created_at,制造"发布很旧但刚抓取"的场景。"""
    return Video(
        id=vid,
        title=f'v{vid}',
        url=f'http://x/{vid}',
        domain='x.com',
        publish_date=publish_date,
        created_at=created_at,
        is_deleted=deleted,
    )


def _seed_cross_sort(session_factory):
    """Seed 一个 publish_date 与 created_at 顺序不一致的场景。

    user 1, sub 10 (special):
      v1: publish 10d ago, created 1h ago  (发布很旧,刚抓回来)
      v2: publish 5d ago,  created 2h ago
      v3: publish 1d ago,  created 3h ago  (发布最新,抓取最早)
    → publish_date desc 顺序: [3, 2, 1]
    → created_at  desc 顺序: [3, 2, 1]  (此处恰巧一致,下面单独测颠倒场景)
    """
    now = datetime.now()
    with session_factory() as s:
        s.add_all(
            [
                _make_video(1, publish_date=now - timedelta(days=10), created_at=now - timedelta(hours=1)),
                _make_video(2, publish_date=now - timedelta(days=5), created_at=now - timedelta(hours=2)),
                _make_video(3, publish_date=now - timedelta(days=1), created_at=now - timedelta(hours=3)),
            ]
        )
        s.add(Subscription(id=10, name='specialA', type='CHANNEL'))
        s.add(UserSubscription(user_id=1, subscription_id=10, is_special_followed=True, is_deleted=False))
        s.add_all(
            [
                SubscriptionVideo(subscription_id=10, video_id=1),
                SubscriptionVideo(subscription_id=10, video_id=2),
                SubscriptionVideo(subscription_id=10, video_id=3),
            ]
        )


def _seed_inverted_sort(session_factory):
    """Seed publish_date desc 与 created_at desc 完全相反的场景(核心 bug 场景)。

    user 1, sub 10 (special):
      v1: publish 1d ago  (发布最新),  created 5h ago (抓取最早)
      v2: publish 3d ago,              created 3h ago
      v3: publish 10d ago (发布最旧),  created 1h ago (抓取最新)

    → publish_date desc: [1, 2, 3]
    → created_at    desc: [3, 2, 1]  (完全颠倒)

    这正是用户报告的 bug:按抓取日期期望看到 v3 在最前(刚抓),
    但旧实现按 publish_date 永远把 v3 排到最后,翻页滚不到 → "看不见"。
    """
    now = datetime.now()
    with session_factory() as s:
        s.add_all(
            [
                _make_video(1, publish_date=now - timedelta(days=1), created_at=now - timedelta(hours=5)),
                _make_video(2, publish_date=now - timedelta(days=3), created_at=now - timedelta(hours=3)),
                _make_video(3, publish_date=now - timedelta(days=10), created_at=now - timedelta(hours=1)),
            ]
        )
        s.add(Subscription(id=10, name='specialA', type='CHANNEL'))
        s.add(UserSubscription(user_id=1, subscription_id=10, is_special_followed=True, is_deleted=False))
        s.add_all(
            [
                SubscriptionVideo(subscription_id=10, video_id=1),
                SubscriptionVideo(subscription_id=10, video_id=2),
                SubscriptionVideo(subscription_id=10, video_id=3),
            ]
        )


def test_sort_by_created_at_orders_by_created_desc(session_factory):
    """sort_by=created_at → 按 created_at desc 排序(而非 publish_date)。"""
    _seed_inverted_sort(session_factory)
    with session_factory() as s:
        ids, _ = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=50, sort_by='created_at')
    # created_at desc: v3 (1h ago) > v2 (3h ago) > v1 (5h ago)
    assert ids == [3, 2, 1]


def test_sort_by_publish_date_orders_by_publish_desc(session_factory):
    """sort_by=publish_date(默认)→ 按 publish_date desc 排序(回归保护)。"""
    _seed_inverted_sort(session_factory)
    with session_factory() as s:
        ids, _ = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=50, sort_by='publish_date')
    # publish_date desc: v1 (1d ago) > v2 (3d ago) > v3 (10d ago)
    assert ids == [1, 2, 3]


def test_sort_by_default_is_publish_date(session_factory):
    """不传 sort_by → 默认 publish_date(向后兼容现有调用)。"""
    _seed_inverted_sort(session_factory)
    with session_factory() as s:
        ids, _ = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=50)
    assert ids == [1, 2, 3]


def test_created_at_cursor_uses_c_namespace(session_factory):
    """sort_by=created_at 生成的游标 key 为 'c',与 publish 的 'p' 隔离。"""
    _seed_inverted_sort(session_factory)
    with session_factory() as s:
        _, cursor = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=1, sort_by='created_at')
    assert cursor is not None
    # decode 出的 key 必须是 created 命名空间
    decoded = decode_cursor(cursor)
    assert decoded is not None
    assert decoded[0] == _CURSOR_KEY_CREATED


def test_publish_cursor_rejected_for_created_sort(session_factory):
    """publish 游标用于 created_at 排序请求 → decode_for_key 返回 None → 回首页。

    模拟用户从"上传日期"翻到第 2 页,切到"抓取日期",前端理论上会清游标;
    但若 URL 残留老游标,后端校验 key 不符 → 不施加 cursor 条件,从首页开始,避免串号。
    """
    _seed_inverted_sort(session_factory)
    # 先用 publish_date 翻一页,拿到 'p' 游标
    with session_factory() as s:
        _, publish_cursor = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=1, sort_by='publish_date')
    assert publish_cursor is not None
    assert decode_cursor(publish_cursor)[0] == _CURSOR_KEY_PUBLISH

    # 把这个 'p' 游标喂给 created_at 请求 → 应被拒(decode_for_key 返回 None)
    assert decode_cursor_for_key(publish_cursor, _CURSOR_KEY_CREATED) is None

    # 实际调用:传入错配游标,等价于首页(返回 created_at desc 的第一条 v3)
    with session_factory() as s:
        ids, _ = fetch_special_follow_video_ids(s, user_id=1, cursor=publish_cursor, limit=1, sort_by='created_at')
    assert ids == [3]


def test_created_at_keyset_pagination_consistent(session_factory):
    """sort_by=created_at 的 keyset 翻页:顺序连续,无重复无跳页。"""
    _seed_inverted_sort(session_factory)
    with session_factory() as s:
        page1, c1 = fetch_special_follow_video_ids(s, user_id=1, cursor=None, limit=1, sort_by='created_at')
        page2, c2 = fetch_special_follow_video_ids(s, user_id=1, cursor=c1, limit=1, sort_by='created_at')
        page3, c3 = fetch_special_follow_video_ids(s, user_id=1, cursor=c2, limit=1, sort_by='created_at')
    assert page1 == [3]
    assert page2 == [2]
    assert page3 == [1]
    assert c1 is not None and c2 is not None
    assert c3 is None  # exhausted


def test_created_at_cursor_roundtrip_with_explicit_encode():
    """手工 encode 'c' 游标 → decode 还原 (ts, id)。"""
    token = encode_cursor(_CURSOR_KEY_CREATED, 1700000000, 99)
    assert decode_cursor_for_key(token, _CURSOR_KEY_CREATED) == (1700000000, 99)
