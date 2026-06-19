"""Tests for Meili recall layer future-video exclusion.

首页全部标签页(category='all')不应召回未来视频(publish_date > now)。
只有 category='preview'(预告 tab)才放行未来视频。
"""
from datetime import datetime, timedelta

from domains.video.application.services.search.meili_indexer import (
    MeiliVideoIndexer,
    _build_recall_filter,
)


def test_build_recall_filter_excludes_future_for_all_category():
    """category='all'(首页全部)必须追加 publish_ts <= now 上界。"""
    fixed_now = datetime(2026, 6, 16, 12, 0, 0)
    now_ts = int(fixed_now.timestamp())

    filters = _build_recall_filter(
        domains=None, time_range='all', duration='all', category='all', now=fixed_now,
    )

    assert f'publish_ts <= {now_ts}' in filters


def test_build_recall_filter_excludes_future_for_unread_category():
    """非 preview 的 category(如 unread)也排除未来视频。"""
    fixed_now = datetime(2026, 6, 16, 12, 0, 0)
    now_ts = int(fixed_now.timestamp())

    filters = _build_recall_filter(
        domains=None, time_range='all', duration='all', category='unread', now=fixed_now,
    )

    assert f'publish_ts <= {now_ts}' in filters


def test_build_recall_filter_allows_future_for_preview_category():
    """category='preview'(预告 tab)放行未来视频,不追加 publish_ts <= now。"""
    fixed_now = datetime(2026, 6, 16, 12, 0, 0)
    now_ts = int(fixed_now.timestamp())

    filters = _build_recall_filter(
        domains=None, time_range='all', duration='all', category='preview', now=fixed_now,
    )

    assert f'publish_ts <= {now_ts}' not in filters


def test_build_recall_filter_future_bound_uses_now_by_default():
    """不传 now 时应使用当前时间(不抛错,且值合理)。"""
    filters = _build_recall_filter(
        domains=None, time_range='all', duration='all', category='all',
    )
    future_bound = [f for f in filters if f.startswith('publish_ts <= ')]
    assert len(future_bound) == 1
    # 上界应接近当前时间(±60s 容差应对执行耗时)
    bound_ts = int(future_bound[0].split('<= ')[1])
    assert abs(bound_ts - int(datetime.now().timestamp())) < 60


def test_build_recall_filter_combines_time_range_and_future_bound():
    """time_range 下界与 publish_ts <= now 上界同时存在(区间合法)。"""
    fixed_now = datetime(2026, 6, 16, 12, 0, 0)
    now_ts = int(fixed_now.timestamp())

    filters = _build_recall_filter(
        domains=None, time_range='week', duration='all', category='all', now=fixed_now,
    )

    week_start_ts = int((fixed_now - timedelta(days=fixed_now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0,
    ).timestamp())
    assert f'publish_ts >= {week_start_ts}' in filters
    assert f'publish_ts <= {now_ts}' in filters


class _FakeSearchResult:
    def __init__(self, hits):
        self._hits = hits

    def get(self, key, default=None):
        if key == 'hits':
            return self._hits
        return default


class _FakeIndex:
    def __init__(self):
        self.last_options = None

    def search(self, query, options):
        self.last_options = dict(options)
        return _FakeSearchResult([
            {'id': 1, 'publish_ts': 1000},
            {'id': 2, 'publish_ts': 2000},
        ])


def _make_indexer_with_fake():
    """构造一个绕过真实 Meili client 的 indexer(避免连接依赖)。"""
    indexer = MeiliVideoIndexer.__new__(MeiliVideoIndexer)
    indexer._session_factory = None
    fake_index = _FakeIndex()
    indexer._index = fake_index
    return indexer, fake_index


def test_recall_threads_category_to_filter_for_search():
    """recall()(搜索场景)把 category 传给 _build_recall_filter。"""
    indexer, fake_index = _make_indexer_with_fake()

    # 通过观察传给 Meili 的 filter 验证 category 是否被透传
    indexer.recall('foo', category='all')
    filters = fake_index.last_options.get('filter', [])
    assert any(f.startswith('publish_ts <= ') for f in filters)
    # 上界是合法 unix 秒(接近真实当前时间即可,容忍主机/容器时钟差异)
    bound = next(f for f in filters if f.startswith('publish_ts <= '))
    bound_ts = int(bound.split('<= ')[1])
    assert abs(bound_ts - int(datetime.now().timestamp())) < 120


def test_recall_preview_does_not_add_future_bound():
    """recall() category='preview' 不追加 publish_ts <= now。"""
    indexer, fake_index = _make_indexer_with_fake()

    indexer.recall('foo', category='preview')
    filters = fake_index.last_options.get('filter', [])
    assert not any(f.startswith('publish_ts <= ') for f in filters)


def test_recall_page_threads_category_to_filter():
    """recall_page()(浏览场景)把 category 传给 _build_recall_filter。"""
    indexer, fake_index = _make_indexer_with_fake()

    indexer.recall_page(category='all')
    filters = fake_index.last_options.get('filter', [])
    assert any(f.startswith('publish_ts <= ') for f in filters)


def test_recall_page_preview_does_not_add_future_bound():
    """recall_page() category='preview' 不追加 publish_ts <= now。"""
    indexer, fake_index = _make_indexer_with_fake()

    indexer.recall_page(category='preview')
    filters = fake_index.last_options.get('filter', [])
    assert not any(f.startswith('publish_ts <= ') for f in filters)
